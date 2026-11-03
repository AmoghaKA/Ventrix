from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.base import BaseAgent
from app.agents.output import (
    AgentOutput,
    EvidenceStatus,
    ExecutionStatus,
)
from app.db.models import Evidence


class VerificationFindingStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    INVALID = "INVALID"
    UNAVAILABLE = "UNAVAILABLE"


class VerificationFinding(BaseModel):
    agent_name: str
    dimension: str
    evidence_references: List[int] = Field(default_factory=list)
    status: VerificationFindingStatus
    issue: Optional[str] = None


class VerificationOutput(BaseModel):
    agent_name: str = "Verification Agent"
    analysis_id: int
    execution_status: ExecutionStatus
    status: EvidenceStatus
    total_findings: int = 0
    checked_references: int = 0
    valid_references: int = 0
    invalid_references: int = 0
    results: List[VerificationFinding] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list)
    specialist_statuses: Dict[str, str] = Field(default_factory=dict)
    error_details: Optional[str] = None


_STATUS_ORDER = {
    EvidenceStatus.UNAVAILABLE: 0,
    EvidenceStatus.UNVERIFIED: 1,
    EvidenceStatus.PARTIALLY_VERIFIED: 2,
    EvidenceStatus.VERIFIED: 3,
}


class VerificationAgent(BaseAgent):
    AGENT_NAME = "Verification Agent"

    def __init__(self, db: Optional[Session] = None) -> None:
        super().__init__(self.AGENT_NAME)
        self.db = db

    async def run(
        self,
        startup_id: int,
        context: Optional[Dict[str, Any]] = None,
    ) -> VerificationOutput:
        try:
            analysis_id = self._analysis_id(context)
            outputs = (context or {}).get("specialist_outputs") or {}
            specialist_errors = (context or {}).get("specialist_errors") or {}
            evidence = self._load_evidence(analysis_id, startup_id)
            return self._build_output(
                analysis_id,
                outputs,
                specialist_errors,
                evidence,
            )
        except Exception as exc:
            self.logger.error(f"Agent {self.name} failed: {exc}")
            return self._error_output(context, exc)

    def structured_error_output(
        self,
        startup_id: int,
        context: Optional[Dict[str, Any]],
        error: Exception,
    ) -> VerificationOutput:
        return self._error_output(context, error)

    def _analysis_id(self, context: Optional[Dict[str, Any]]) -> int:
        if not context or context.get("analysis_id") is None:
            raise ValueError("analysis_id is required in the agent context")
        try:
            analysis_id = int(context["analysis_id"])
        except (TypeError, ValueError) as exc:
            raise ValueError("analysis_id must be a positive integer") from exc
        if analysis_id <= 0:
            raise ValueError("analysis_id must be a positive integer")
        return analysis_id

    def _context_analysis_id(self, context: Optional[Dict[str, Any]]) -> int:
        try:
            return int((context or {}).get("analysis_id", 0) or 0)
        except (TypeError, ValueError):
            return 0

    def _load_evidence(
        self,
        analysis_id: int,
        startup_id: int,
    ) -> Dict[int, Evidence]:
        if self.db is None:
            raise ValueError("A database session is required to load evidence")

        query = self.db.query(Evidence).filter(
            Evidence.analysis_id == analysis_id
        )
        if startup_id:
            query = query.filter(Evidence.startup_id == startup_id)
        return {item.id: item for item in query.all()}

    def _build_output(
        self,
        analysis_id: int,
        outputs: Dict[str, Any],
        specialist_errors: Dict[str, Any],
        evidence_by_id: Dict[int, Evidence],
    ) -> VerificationOutput:
        results: List[VerificationFinding] = []
        issues: List[str] = []
        specialist_statuses: Dict[str, str] = {}
        checked_references = 0
        valid_references = 0
        invalid_references = 0
        total_findings = 0

        for agent_key, raw_output in outputs.items():
            try:
                output = self._coerce_output(raw_output)
            except Exception as exc:
                issues.append(f"{agent_key}: invalid agent output ({exc})")
                specialist_statuses[agent_key] = "FAILED"
                continue

            specialist_statuses[agent_key] = output.execution_status.value
            reference_statuses = {
                reference.evidence_id: reference.verification_status
                for reference in output.evidence_references
            }

            for finding in output.findings:
                total_findings += 1
                references = list(finding.evidence_references)
                checked_references += len(references)

                if not references:
                    if finding.evidence_status == EvidenceStatus.UNAVAILABLE:
                        status = VerificationFindingStatus.UNAVAILABLE
                        issue = None
                    else:
                        status = VerificationFindingStatus.INVALID
                        issue = (
                            f"{finding.dimension} claims "
                            f"{finding.evidence_status.value} evidence but has "
                            "no evidence references."
                        )
                else:
                    missing = [
                        evidence_id
                        for evidence_id in references
                        if evidence_id not in evidence_by_id
                    ]
                    invalid_references += len(missing)
                    valid_references += len(references) - len(missing)

                    if missing:
                        status = VerificationFindingStatus.INVALID
                        issue = (
                            f"{finding.dimension} references evidence that "
                            f"does not belong to analysis {analysis_id}: "
                            + ", ".join(str(item) for item in missing)
                        )
                    else:
                        actual_status = self._aggregate_status(
                            self._normalise_status(
                                evidence_by_id[evidence_id].verification_status
                            )
                            for evidence_id in references
                        )
                        claimed_status = finding.evidence_status
                        status = self._verification_status(actual_status)
                        issue = None
                        if (
                            _STATUS_ORDER[claimed_status]
                            > _STATUS_ORDER[actual_status]
                        ):
                            issue = (
                                f"{finding.dimension} claims "
                                f"{claimed_status.value} evidence but stored "
                                f"evidence is {actual_status.value}."
                            )

                        for evidence_id in references:
                            reference_status = reference_statuses.get(evidence_id)
                            stored_status = self._normalise_status(
                                evidence_by_id[evidence_id].verification_status
                            )
                            if (
                                reference_status is not None
                                and reference_status != stored_status
                            ):
                                issues.append(
                                    f"{finding.dimension} reference "
                                    f"{evidence_id} reports "
                                    f"{reference_status.value} but stored "
                                    f"evidence is {stored_status.value}."
                                )

                if issue:
                    issues.append(issue)
                results.append(
                    VerificationFinding(
                        agent_name=output.agent_name,
                        dimension=finding.dimension,
                        evidence_references=references,
                        status=status,
                        issue=issue,
                    )
                )

        for agent_key, error in specialist_errors.items():
            specialist_statuses[agent_key] = "FAILED"
            issues.append(f"{agent_key}: {error}")

        status = self._overall_status(results)
        execution_status = (
            ExecutionStatus.PARTIAL
            if issues or specialist_errors
            else ExecutionStatus.SUCCESS
        )
        if not outputs:
            execution_status = ExecutionStatus.FAILED
            issues.append("No specialist outputs were available to verify.")

        return VerificationOutput(
            analysis_id=analysis_id,
            execution_status=execution_status,
            status=status,
            total_findings=total_findings,
            checked_references=checked_references,
            valid_references=valid_references,
            invalid_references=invalid_references,
            results=results,
            issues=issues,
            specialist_statuses=specialist_statuses,
            error_details=None,
        )

    def _coerce_output(self, output: Any) -> AgentOutput:
        if isinstance(output, AgentOutput):
            return output
        if isinstance(output, dict):
            return AgentOutput.model_validate(output)
        raise TypeError(f"Unsupported agent output type: {type(output).__name__}")

    def _verification_status(
        self,
        status: EvidenceStatus,
    ) -> VerificationFindingStatus:
        return VerificationFindingStatus(status.value)

    def _overall_status(
        self,
        results: List[VerificationFinding],
    ) -> EvidenceStatus:
        if not results:
            return EvidenceStatus.UNAVAILABLE

        statuses = []
        for result in results:
            if result.status == VerificationFindingStatus.INVALID:
                statuses.append(EvidenceStatus.UNAVAILABLE)
            else:
                statuses.append(EvidenceStatus(result.status.value))
        return self._aggregate_status(statuses)

    def _aggregate_status(self, statuses) -> EvidenceStatus:
        values = list(statuses)
        if not values:
            return EvidenceStatus.UNAVAILABLE
        if all(status == EvidenceStatus.VERIFIED for status in values):
            return EvidenceStatus.VERIFIED
        if any(
            status in {EvidenceStatus.VERIFIED, EvidenceStatus.PARTIALLY_VERIFIED}
            for status in values
        ):
            return EvidenceStatus.PARTIALLY_VERIFIED
        if any(status == EvidenceStatus.UNVERIFIED for status in values):
            return EvidenceStatus.UNVERIFIED
        return EvidenceStatus.UNAVAILABLE

    def _normalise_status(self, value: Any) -> EvidenceStatus:
        if isinstance(value, EvidenceStatus):
            return value
        normalised = str(value or "").strip().upper()
        try:
            return EvidenceStatus(normalised)
        except ValueError:
            return EvidenceStatus.UNVERIFIED

    def _error_output(
        self,
        context: Optional[Dict[str, Any]],
        error: Exception,
    ) -> VerificationOutput:
        return VerificationOutput(
            analysis_id=self._context_analysis_id(context),
            execution_status=ExecutionStatus.FAILED,
            status=EvidenceStatus.UNAVAILABLE,
            issues=["Verification could not be completed."],
            error_details=str(error),
        )
