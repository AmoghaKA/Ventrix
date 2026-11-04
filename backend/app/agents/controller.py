import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

import logging

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.agents.evidence_agent import EvidenceAgent
from app.agents.orchestrator import AgentDefinition, resolve_agent
from app.agents.output import AgentOutput, ExecutionStatus
from app.agents.verification import VerificationAgent, VerificationOutput
from app.data import Cache, EvidenceStore, PublicDataRetriever, UnsafeURLError
from app.db.models import (
    Analysis,
    DueDiligenceWorkflow,
    Evidence,
    Startup,
    WorkflowActivityLog,
    WorkflowAgentStatus,
    WorkflowCheckpoint,
)
from app.schemas.controller import ControllerAssessment
from app.llm.gateway import llm_gateway
from app.workflows.report import generate_final_report
from app.workflows.status import (
    WorkflowAgentExecutionStatus as AgentStatus,
    WorkflowStatus,
)

_UNSET = object()

logger = logging.getLogger("ventrix.controller")


def _assessment_payload(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return value

WORKFLOW_STEPS: Tuple[Tuple[str, str, int], ...] = (
    ("data_retrieval", "Data Retrieval", 1),
    ("controller", "Controller Agent", 2),
    ("financial", "Financial Agent", 3),
    ("marketing", "Marketing Agent", 4),
    ("legal", "Legal Agent", 5),
    ("verification", "Verification Agent", 6),
    ("report", "Final Report", 7),
)


class ControllerAgent:
    def __init__(
        self,
        db: Session,
        workflow: DueDiligenceWorkflow,
        *,
        retry_limit: Optional[int] = None,
        retry_backoff_seconds: float = 0.05,
        max_pages: int = 5,
        llm_gateway_instance=llm_gateway,
    ) -> None:
        self.db = db
        self.workflow_id = workflow.id
        self.retry_limit = (
            workflow.retry_limit if retry_limit is None else retry_limit
        )
        self.retry_backoff_seconds = retry_backoff_seconds
        self.max_pages = max_pages
        self.llm = llm_gateway_instance
        self._ensure_status_rows()

    def _workflow(self) -> DueDiligenceWorkflow:
        workflow = self.db.get(DueDiligenceWorkflow, self.workflow_id)
        if workflow is None:
            raise LookupError(
                f"Workflow {self.workflow_id} was not found."
            )
        return workflow

    def _analysis(self) -> Analysis:
        workflow = self._workflow()
        analysis = self.db.get(Analysis, workflow.analysis_id)
        if analysis is None:
            raise LookupError(
                f"Analysis {workflow.analysis_id} was not found."
            )
        return analysis

    def _startup(self) -> Startup:
        workflow = self._workflow()
        if workflow.startup_id is not None:
            startup = self.db.get(Startup, workflow.startup_id)
            if startup is not None:
                return startup

        analysis = self._analysis()
        startup = EvidenceStore(self.db).ensure_startup(
            analysis.startup_name,
            analysis.website,
            industry=analysis.industry,
        )
        workflow.startup_id = startup.id
        self.db.flush()
        return startup

    def _ensure_status_rows(self) -> Dict[str, WorkflowAgentStatus]:
        workflow = self._workflow()
        rows: Dict[str, WorkflowAgentStatus] = {}
        changed = False
        for key, name, sequence in WORKFLOW_STEPS:
            row = (
                self.db.query(WorkflowAgentStatus)
                .filter(
                    WorkflowAgentStatus.workflow_id == workflow.id,
                    WorkflowAgentStatus.agent_key == key,
                )
                .one_or_none()
            )
            if row is None:
                row = WorkflowAgentStatus(
                    workflow_id=workflow.id,
                    analysis_id=workflow.analysis_id,
                    agent_key=key,
                    agent_name=name,
                    sequence=sequence,
                    status=AgentStatus.PENDING.value,
                )
                self.db.add(row)
                changed = True
            rows[key] = row
        if changed:
            self.db.commit()
        return rows

    def _status_row(self, agent_key: str) -> WorkflowAgentStatus:
        row = (
            self.db.query(WorkflowAgentStatus)
            .filter(
                WorkflowAgentStatus.workflow_id == self.workflow_id,
                WorkflowAgentStatus.agent_key == agent_key,
            )
            .one_or_none()
        )
        if row is None:
            self._ensure_status_rows()
            row = (
                self.db.query(WorkflowAgentStatus)
                .filter(
                    WorkflowAgentStatus.workflow_id == self.workflow_id,
                    WorkflowAgentStatus.agent_key == agent_key,
                )
                .one_or_none()
            )
        if row is None:
            raise LookupError(f"Unknown workflow step '{agent_key}'.")
        return row

    def set_step_status(
        self,
        agent_key: str,
        status: AgentStatus,
        *,
        attempt_count: Optional[int] = None,
        output: Any = _UNSET,
        error_details: Any = _UNSET,
    ) -> WorkflowAgentStatus:
        row = self._status_row(agent_key)
        now = datetime.utcnow()
        row.status = status.value
        if attempt_count is not None:
            row.attempt_count = attempt_count
        if status == AgentStatus.RUNNING and row.started_at is None:
            row.started_at = now
        if status in {AgentStatus.COMPLETED, AgentStatus.FAILED}:
            row.completed_at = now
        if output is not _UNSET:
            row.output = jsonable_encoder(output) if output is not None else None
        if error_details is not _UNSET:
            row.error_details = (
                str(error_details) if error_details is not None else None
            )
        self.db.commit()
        return row

    def log(
        self,
        event: str,
        message: str,
        *,
        level: str = "INFO",
        agent_key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        workflow = self._workflow()
        self.db.add(
            WorkflowActivityLog(
                workflow_id=workflow.id,
                analysis_id=workflow.analysis_id,
                level=level,
                event=event,
                agent_key=agent_key,
                message=message,
                meta=jsonable_encoder(metadata or {}),
            )
        )
        self.db.commit()

    def persist_state(
        self,
        state: Dict[str, Any],
        step: str,
        *,
        status: Optional[WorkflowStatus] = None,
        error_details: Any = _UNSET,
        report: Any = _UNSET,
    ) -> None:
        workflow = self._workflow()
        now = datetime.utcnow()
        workflow.state = jsonable_encoder(state)
        workflow.current_step = step
        if status is not None:
            workflow.status = status.value
            if status == WorkflowStatus.RUNNING and workflow.started_at is None:
                workflow.started_at = now
            if status in {WorkflowStatus.COMPLETED, WorkflowStatus.FAILED}:
                workflow.completed_at = now
        if error_details is not _UNSET:
            workflow.error_details = (
                str(error_details) if error_details is not None else None
            )
        if report is not _UNSET:
            workflow.report = (
                jsonable_encoder(report) if report is not None else None
            )
        self.db.add(
            WorkflowCheckpoint(
                workflow_id=workflow.id,
                step=step,
                state=jsonable_encoder(state),
            )
        )
        self.db.commit()

    def save_checkpoint(self, step: str, state: Dict[str, Any]) -> None:
        workflow = self._workflow()
        self.db.add(
            WorkflowCheckpoint(
                workflow_id=workflow.id,
                step=step,
                state=jsonable_encoder(state),
            )
        )
        self.db.commit()

    def begin_workflow(self) -> None:
        workflow = self._workflow()
        analysis = self._analysis()
        workflow.status = WorkflowStatus.RUNNING.value
        workflow.current_step = "data_retrieval"
        if workflow.started_at is None:
            workflow.started_at = datetime.utcnow()
        analysis.status = "running"
        self.db.commit()
        self.log(
            "workflow_started",
            "Due diligence workflow started.",
            metadata={"workflow_id": workflow.id},
        )

    def retrieve_data(self) -> Dict[str, Any]:
        workflow = self._workflow()
        analysis = self._analysis()
        startup = self._startup()
        self.db.commit()

        self.set_step_status("data_retrieval", AgentStatus.RUNNING)
        self.log(
            "data_retrieval_started",
            "Checking for existing evidence before retrieval.",
            agent_key="data_retrieval",
        )

        existing = (
            self.db.query(Evidence)
            .filter(Evidence.analysis_id == analysis.id)
            .count()
        )
        if existing:
            self.set_step_status(
                "data_retrieval",
                AgentStatus.COMPLETED,
                output={"status": "SKIPPED", "existing_evidence": existing},
            )
            self.log(
                "data_retrieval_skipped",
                f"Using {existing} existing evidence record(s).",
                agent_key="data_retrieval",
            )
            return {
                "startup_id": startup.id,
                "retrieval": {
                    "status": "SKIPPED",
                    "existing_evidence": existing,
                },
            }

        total_attempts = self.retry_limit + 1
        last_error = "Data retrieval failed."
        for attempt in range(1, total_attempts + 1):
            self.set_step_status(
                "data_retrieval",
                AgentStatus.RUNNING,
                attempt_count=attempt,
            )
            if attempt > 1:
                self.log(
                    "data_retrieval_retry",
                    f"Retrying data retrieval (attempt {attempt}).",
                    level="WARNING",
                    agent_key="data_retrieval",
                )
            try:
                retriever = PublicDataRetriever(
                    cache=Cache(self.db),
                    max_pages=self.max_pages,
                )
                report = retriever.retrieve(
                    analysis.website,
                    max_pages=self.max_pages,
                )
                result = EvidenceStore(self.db).store_report(
                    analysis,
                    startup,
                    report,
                )
                self.db.commit()
                payload = {
                    "status": "COMPLETED",
                    "retrieved_sources": result.total_sources,
                    "stored_evidence": result.stored,
                    "updated_evidence": result.updated,
                    "skipped_sources": result.skipped,
                }
                self.set_step_status(
                    "data_retrieval",
                    AgentStatus.COMPLETED,
                    output=payload,
                )
                self.log(
                    "data_retrieval_completed",
                    (
                        f"Retrieved {result.total_sources} source(s); stored "
                        f"{result.stored} and updated {result.updated}."
                    ),
                    agent_key="data_retrieval",
                    metadata=payload,
                )
                return {"startup_id": startup.id, "retrieval": payload}
            except UnsafeURLError as exc:
                self.db.rollback()
                last_error = str(exc)
                self.set_step_status(
                    "data_retrieval",
                    AgentStatus.FAILED,
                    output={"status": "FAILED", "error": last_error},
                    error_details=last_error,
                )
                self.log(
                    "data_retrieval_failed",
                    f"Data retrieval was blocked: {last_error}",
                    level="ERROR",
                    agent_key="data_retrieval",
                )
                return {
                    "startup_id": startup.id,
                    "retrieval": {"status": "FAILED", "error": last_error},
                }
            except Exception as exc:
                self.db.rollback()
                last_error = str(exc)
                self.log(
                    "data_retrieval_error",
                    f"Data retrieval attempt {attempt} failed: {last_error}",
                    level="WARNING",
                    agent_key="data_retrieval",
                )
                if attempt < total_attempts:
                    time.sleep(self.retry_backoff_seconds * attempt)

        self.set_step_status(
            "data_retrieval",
            AgentStatus.FAILED,
            output={"status": "FAILED", "error": last_error},
            error_details=last_error,
        )
        self.log(
            "data_retrieval_failed",
            f"Data retrieval failed after {total_attempts} attempt(s).",
            level="ERROR",
            agent_key="data_retrieval",
        )
        return {
            "startup_id": startup.id,
            "retrieval": {"status": "FAILED", "error": last_error},
        }

    def prepare_controller(self) -> Dict[str, Any]:
        workflow = self._workflow()
        startup = self._startup()
        self.db.commit()
        self.set_step_status("controller", AgentStatus.RUNNING)
        workflow.current_step = "controller"
        self.db.commit()
        self.log(
            "controller_started",
            "Controller Agent is preparing specialist delegation.",
            agent_key="controller",
        )
        return {
            "startup_id": startup.id,
            "current_step": "controller",
        }

    async def run_specialist(
        self,
        agent_key: str,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        definition = resolve_agent(agent_key)
        startup_id = int(state["startup_id"])
        analysis_id = int(state["analysis_id"])
        total_attempts = self.retry_limit + 1
        last_error = f"{definition.name} failed."

        self.set_step_status(definition.key, AgentStatus.RUNNING)
        self.log(
            "agent_started",
            f"{definition.name} started.",
            agent_key=definition.key,
        )

        for attempt in range(1, total_attempts + 1):
            self.set_step_status(
                definition.key,
                AgentStatus.RUNNING,
                attempt_count=attempt,
            )
            if attempt > 1:
                self.log(
                    "agent_retry",
                    f"{definition.name} retry attempt {attempt}.",
                    level="WARNING",
                    agent_key=definition.key,
                )

            output: Optional[AgentOutput] = None
            try:
                agent = definition.agent_class(self.db)
                output = await agent.execute(
                    startup_id,
                    {"analysis_id": analysis_id},
                )
                payload = self._output_payload(output)
                if output.execution_status != ExecutionStatus.FAILED:
                    self.set_step_status(
                        definition.key,
                        AgentStatus.COMPLETED,
                        output=payload,
                    )
                    self.log(
                        "agent_completed",
                        (
                            f"{definition.name} completed with status "
                            f"{output.execution_status.value}."
                        ),
                        agent_key=definition.key,
                    )
                    self.save_checkpoint(
                        f"agent:{definition.key}",
                        {
                            "workflow_id": self.workflow_id,
                            "agent_key": definition.key,
                            "attempts": attempt,
                            "output": payload,
                        },
                    )
                    return {
                        "specialist_outputs": {definition.key: payload},
                        "attempts": {definition.key: attempt},
                    }
                last_error = output.error_details or last_error
            except Exception as exc:
                last_error = str(exc)
                payload = None

            if attempt < total_attempts:
                self.log(
                    "agent_retry_scheduled",
                    (
                        f"{definition.name} failed on attempt {attempt}: "
                        f"{last_error}"
                    ),
                    level="WARNING",
                    agent_key=definition.key,
                )
                await asyncio.sleep(self.retry_backoff_seconds * attempt)
                continue

            self.set_step_status(
                definition.key,
                AgentStatus.FAILED,
                output=payload,
                error_details=last_error,
            )
            self.log(
                "agent_failed",
                (
                    f"{definition.name} failed after {total_attempts} "
                    f"attempt(s): {last_error}"
                ),
                level="ERROR",
                agent_key=definition.key,
            )
            self.save_checkpoint(
                f"agent:{definition.key}:failed",
                {
                    "workflow_id": self.workflow_id,
                    "agent_key": definition.key,
                    "attempts": attempt,
                    "error": last_error,
                },
            )
            return {
                "specialist_errors": {definition.key: last_error},
                "attempts": {definition.key: attempt},
            }

        return {
            "specialist_errors": {definition.key: last_error},
            "attempts": {definition.key: total_attempts},
        }

    def aggregate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        outputs = state.get("specialist_outputs") or {}
        errors = state.get("specialist_errors") or {}

        risks = [
            str(output.get("risk_level", "UNKNOWN"))
            for output in outputs.values()
        ]
        risk_order = {
            "UNKNOWN": 0,
            "LOW": 1,
            "MEDIUM": 2,
            "HIGH": 3,
            "CRITICAL": 4,
        }
        known = [risk for risk in risks if risk in risk_order and risk != "UNKNOWN"]
        overall_risk = (
            max(known, key=lambda risk: risk_order[risk])
            if known
            else "UNKNOWN"
        )
        statuses = [
            str(output.get("evidence_status", "UNAVAILABLE"))
            for output in outputs.values()
        ]
        if not statuses:
            evidence_status = "UNAVAILABLE"
        elif all(status == "VERIFIED" for status in statuses):
            evidence_status = "VERIFIED"
        elif any(
            status in {"VERIFIED", "PARTIALLY_VERIFIED"}
            for status in statuses
        ):
            evidence_status = "PARTIALLY_VERIFIED"
        elif any(status == "UNVERIFIED" for status in statuses):
            evidence_status = "UNVERIFIED"
        else:
            evidence_status = "UNAVAILABLE"

        missing = []
        seen = set()
        for output in outputs.values():
            for item in output.get("missing_information", []):
                if item in seen:
                    continue
                seen.add(item)
                missing.append(item)

        aggregation = {
            "overall_risk": overall_risk,
            "evidence_status": evidence_status,
            "completed_agents": sorted(outputs),
            "failed_agents": sorted(errors),
            "missing_information": missing,
            "specialist_count": len(outputs),
        }

        workflow = self._workflow()
        workflow.current_step = "aggregation"
        self.db.commit()
        self.log(
            "specialist_outputs_aggregated",
            (
                f"Aggregated {len(outputs)} specialist output(s); "
                f"{len(errors)} failure(s)."
            ),
            agent_key="controller",
            metadata=aggregation,
        )
        return {"aggregation": aggregation, "current_step": "aggregation"}

    async def run_verification(
        self,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        startup_id = int(state["startup_id"])
        analysis_id = int(state["analysis_id"])
        total_attempts = self.retry_limit + 1
        last_error = "Verification failed."
        payload: Optional[Dict[str, Any]] = None

        self.set_step_status("verification", AgentStatus.RUNNING)
        self.log(
            "verification_started",
            "Verification Agent started.",
            agent_key="verification",
        )

        for attempt in range(1, total_attempts + 1):
            self.set_step_status(
                "verification",
                AgentStatus.RUNNING,
                attempt_count=attempt,
            )
            if attempt > 1:
                self.log(
                    "verification_retry",
                    f"Verification retry attempt {attempt}.",
                    level="WARNING",
                    agent_key="verification",
                )
            try:
                agent = VerificationAgent(self.db)
                output = await agent.execute(
                    startup_id,
                    {
                        "analysis_id": analysis_id,
                        "specialist_outputs": state.get(
                            "specialist_outputs", {}
                        ),
                        "specialist_errors": state.get(
                            "specialist_errors", {}
                        ),
                    },
                )
                if isinstance(output, VerificationOutput):
                    payload = output.model_dump(mode="json")
                    if output.execution_status != ExecutionStatus.FAILED:
                        self.set_step_status(
                            "verification",
                            AgentStatus.COMPLETED,
                            output=payload,
                        )
                        self.log(
                            "verification_completed",
                            (
                                "Verification completed with status "
                                f"{output.status.value}."
                            ),
                            agent_key="verification",
                        )
                        return {"verification": payload}
                    last_error = output.error_details or last_error
                else:
                    payload = jsonable_encoder(output)
                    last_error = "Verification returned an unsupported output."
            except Exception as exc:
                last_error = str(exc)

            if attempt < total_attempts:
                await asyncio.sleep(self.retry_backoff_seconds * attempt)
                continue

        self.set_step_status(
            "verification",
            AgentStatus.FAILED,
            output=payload,
            error_details=last_error,
        )
        self.log(
            "verification_failed",
            f"Verification failed after {total_attempts} attempt(s): {last_error}",
            level="ERROR",
            agent_key="verification",
        )
        return {
            "verification_error": last_error,
            "verification": payload,
        }

    async def generate_report(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self.set_step_status("report", AgentStatus.RUNNING)
        self.log(
            "report_started",
            "Final report generation started.",
            agent_key="report",
        )

        try:
            analysis = self._analysis()
            startup = self._startup()
            controller_assessment = await self._assess(
                analysis,
                startup,
                state.get("specialist_outputs", {}),
                state.get("specialist_errors", {}),
                state.get("verification"),
            )
            report = generate_final_report(
                analysis,
                startup,
                state.get("specialist_outputs", {}),
                state.get("specialist_errors", {}),
                state.get("verification"),
                state.get("aggregation"),
                workflow_id=self.workflow_id,
            )
            report["controller_assessment"] = _assessment_payload(controller_assessment)
            workflow = self._workflow()
            workflow.report = jsonable_encoder(report)
            workflow.status = WorkflowStatus.COMPLETED.value
            workflow.current_step = "completed"
            workflow.completed_at = datetime.utcnow()
            analysis.status = "completed"
            analysis.overall_assessment = report.get("overall_assessment")
            self.db.commit()

            self.set_step_status(
                "report",
                AgentStatus.COMPLETED,
                output={
                    "title": report.get("title"),
                    "overall_risk": report.get("overall_risk"),
                    "overall_assessment": report.get("overall_assessment"),
                },
            )
            self.set_step_status("controller", AgentStatus.COMPLETED)
            self.log(
                "workflow_completed",
                "Final report generated and workflow completed.",
                agent_key="controller",
                metadata={
                    "overall_risk": report.get("overall_risk"),
                    "failed_agents": report.get("failed_agents", []),
                },
            )
            self.save_checkpoint(
                "completed",
                {
                    "workflow_id": self.workflow_id,
                    "workflow_status": WorkflowStatus.COMPLETED.value,
                    "report": report,
                },
            )
            return {
                "report": report,
                "workflow_status": WorkflowStatus.COMPLETED.value,
                "current_step": "completed",
            }
        except Exception as exc:
            self.set_step_status(
                "report",
                AgentStatus.FAILED,
                error_details=str(exc),
            )
            raise

    async def _assess(
        self,
        analysis: Analysis,
        startup: Startup,
        specialist_outputs: Dict[str, Any],
        specialist_errors: Dict[str, Any],
        verification: Optional[Dict[str, Any]],
    ) -> ControllerAssessment:
        compact_outputs = {
            key: {
                "status": value.get("execution_status"),
                "risk_level": value.get("risk_level"),
                "evidence_status": value.get("evidence_status"),
                "investor_impact": value.get("investor_impact"),
                "missing_information": value.get("missing_information", []),
            }
            for key, value in specialist_outputs.items()
        }
        prompt = (
            "You are the VENTRIX Controller Agent. Summarize the due diligence inputs below. "
            "Do not fabricate financials, legal, market, or source data. Label unavailable information clearly.\n\n"
            f"Startup: {analysis.startup_name} ({analysis.website})\n"
            f"Industry: {analysis.industry or 'Not provided'}\n"
            f"Country: {analysis.country or 'Not provided'}\n"
            f"Specialist summaries: {compact_outputs}\n"
            f"Specialist errors: {specialist_errors}\n"
            f"Verification status: {verification.get('verification_status') if isinstance(verification, dict) else verification}\n\n"
            "Return only a valid JSON object with keys: summary, key_risks, missing_information, recommended_next_steps."
        )
        for attempt in range(1, 4):
            try:
                result = await self.llm.generate(
                    agent_name="Controller Agent",
                    prompt=prompt,
                    response_schema=ControllerAssessment,
                )
                if result.parsed is not None:
                    return result.parsed
                logger.warning(
                    "Controller LLM returned an unparseable response on attempt %s.",
                    attempt,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Controller LLM assessment failed on attempt %s: %s", attempt, exc)

        return ControllerAssessment(
            summary="Controller assessment unavailable; specialist outputs retained for review.",
            key_risks=[],
            missing_information=list(specialist_errors.values()) or ["No additional information provided."],
            recommended_next_steps=["Review specialist agent outputs and evidence."],
        )

    def fail_workflow(self, error: str) -> Dict[str, Any]:
        workflow = self._workflow()
        analysis = self._analysis()
        workflow.status = WorkflowStatus.FAILED.value
        workflow.current_step = "failed"
        workflow.error_details = str(error)
        workflow.completed_at = datetime.utcnow()
        analysis.status = "failed"
        self.db.commit()

        self.set_step_status(
            "controller",
            AgentStatus.FAILED,
            error_details=str(error),
        )
        self.log(
            "workflow_failed",
            f"Workflow failed: {error}",
            level="ERROR",
            agent_key="controller",
        )
        self.save_checkpoint(
            "failed",
            {
                "workflow_id": self.workflow_id,
                "workflow_status": WorkflowStatus.FAILED.value,
                "error": str(error),
            },
        )
        return {
            "workflow_status": WorkflowStatus.FAILED.value,
            "current_step": "failed",
            "error_details": str(error),
        }

    def _output_payload(self, output: Any) -> Dict[str, Any]:
        if isinstance(output, AgentOutput):
            return output.model_dump(mode="json")
        if hasattr(output, "model_dump"):
            return output.model_dump(mode="json")
        return jsonable_encoder(output)

    def agent_definitions(self) -> List[AgentDefinition]:
        keys: Sequence[str] = ("financial", "marketing", "legal")
        return [resolve_agent(key) for key in keys]
