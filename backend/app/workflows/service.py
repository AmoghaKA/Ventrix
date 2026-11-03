from typing import Optional

from sqlalchemy.orm import Session

from app.agents.controller import WORKFLOW_STEPS, ControllerAgent
from app.core.config import settings
from app.core.logging import logger
from app.db.models import (
    Analysis,
    DueDiligenceWorkflow,
    WorkflowActivityLog,
    WorkflowAgentStatus,
)
from app.db.session import SessionLocal
from app.workflows.due_diligence_graph import run_due_diligence_workflow
from app.workflows.status import (
    WorkflowAgentExecutionStatus as AgentStatus,
    WorkflowStatus,
)


class WorkflowAlreadyRunningError(RuntimeError):
    def __init__(self, workflow: DueDiligenceWorkflow) -> None:
        self.workflow = workflow
        super().__init__(
            f"Workflow {workflow.id} is already {workflow.status}."
        )


class WorkflowNotFoundError(LookupError):
    pass


def create_workflow(
    db: Session,
    analysis_id: int,
    *,
    retry_limit: int = 2,
) -> DueDiligenceWorkflow:
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise LookupError(f"Analysis {analysis_id} was not found.")

    active = (
        db.query(DueDiligenceWorkflow)
        .filter(
            DueDiligenceWorkflow.analysis_id == analysis_id,
            DueDiligenceWorkflow.status.in_(
                [WorkflowStatus.PENDING.value, WorkflowStatus.RUNNING.value]
            ),
        )
        .order_by(DueDiligenceWorkflow.id.desc())
        .first()
    )
    if active is not None:
        raise WorkflowAlreadyRunningError(active)

    workflow = DueDiligenceWorkflow(
        analysis_id=analysis.id,
        startup_id=None,
        status=WorkflowStatus.PENDING.value,
        current_step="pending",
        retry_limit=retry_limit,
        state={},
    )
    db.add(workflow)
    db.flush()

    for key, name, sequence in WORKFLOW_STEPS:
        db.add(
            WorkflowAgentStatus(
                workflow_id=workflow.id,
                analysis_id=analysis.id,
                agent_key=key,
                agent_name=name,
                sequence=sequence,
                status=AgentStatus.PENDING.value,
            )
        )

    analysis.status = "running"
    db.add(
        WorkflowActivityLog(
            workflow_id=workflow.id,
            analysis_id=analysis.id,
            level="INFO",
            event="workflow_queued",
            agent_key="controller",
            message="Due diligence workflow queued.",
            meta={"retry_limit": retry_limit},
        )
    )
    db.commit()
    db.refresh(workflow)
    return workflow


def latest_workflow(
    db: Session,
    analysis_id: int,
) -> Optional[DueDiligenceWorkflow]:
    return (
        db.query(DueDiligenceWorkflow)
        .filter(DueDiligenceWorkflow.analysis_id == analysis_id)
        .order_by(DueDiligenceWorkflow.id.desc())
        .first()
    )


def require_latest_workflow(
    db: Session,
    analysis_id: int,
) -> DueDiligenceWorkflow:
    workflow = latest_workflow(db, analysis_id)
    if workflow is None:
        raise WorkflowNotFoundError(
            f"No workflow exists for analysis {analysis_id}."
        )
    return workflow


async def run_workflow_background(
    workflow_id: int,
    *,
    retry_limit: Optional[int] = None,
    retry_backoff_seconds: Optional[float] = None,
    max_pages: Optional[int] = None,
) -> None:
    db = SessionLocal()
    try:
        workflow = db.get(DueDiligenceWorkflow, workflow_id)
        if workflow is None:
            logger.error("Workflow %s disappeared before execution.", workflow_id)
            return
        if workflow.status in {
            WorkflowStatus.COMPLETED.value,
            WorkflowStatus.FAILED.value,
        }:
            return

        try:
            await run_due_diligence_workflow(
                workflow_id,
                db,
                retry_limit=retry_limit,
                retry_backoff_seconds=(
                    settings.WORKFLOW_RETRY_BACKOFF_SECONDS
                    if retry_backoff_seconds is None
                    else retry_backoff_seconds
                ),
                max_pages=(
                    settings.WORKFLOW_MAX_PAGES if max_pages is None else max_pages
                ),
            )
            final = db.get(DueDiligenceWorkflow, workflow_id)
            if (
                final is not None
                and final.status
                in {WorkflowStatus.PENDING.value, WorkflowStatus.RUNNING.value}
            ):
                ControllerAgent(db, final).fail_workflow(
                    "Workflow ended without reaching a terminal state."
                )
        except Exception as exc:
            logger.exception("Workflow %s failed unexpectedly.", workflow_id)
            try:
                db.rollback()
                failed = db.get(DueDiligenceWorkflow, workflow_id)
                if failed is not None and failed.status in {
                    WorkflowStatus.PENDING.value,
                    WorkflowStatus.RUNNING.value,
                }:
                    ControllerAgent(db, failed).fail_workflow(str(exc))
            except Exception:
                logger.exception(
                    "Could not persist failure for workflow %s.",
                    workflow_id,
                )
                db.rollback()
    finally:
        db.close()
