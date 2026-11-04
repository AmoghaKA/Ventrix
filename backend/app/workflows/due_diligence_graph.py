from typing import Annotated, Any, Dict, Optional, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.agents.controller import ControllerAgent
from app.db.models import DueDiligenceWorkflow
from app.workflows.status import WorkflowStatus


def merge_dicts(
    left: Optional[Dict[str, Any]],
    right: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    merged = dict(left or {})
    merged.update(right or {})
    return merged


class DueDiligenceState(TypedDict, total=False):
    workflow_id: int
    analysis_id: int
    startup_id: int
    workflow_status: str
    current_step: str
    specialist_outputs: Annotated[Dict[str, Any], merge_dicts]
    specialist_errors: Annotated[Dict[str, Any], merge_dicts]
    attempts: Annotated[Dict[str, int], merge_dicts]
    retrieval: Optional[Dict[str, Any]]
    aggregation: Optional[Dict[str, Any]]
    verification: Optional[Dict[str, Any]]
    verification_error: Optional[str]
    report: Optional[Dict[str, Any]]
    error_details: Optional[str]


def _state_snapshot(
    state: Dict[str, Any],
    updates: Dict[str, Any],
) -> Dict[str, Any]:
    snapshot = dict(state)
    snapshot.update(updates)
    return snapshot


def _retrieval_node(
    controller: ControllerAgent,
    state: DueDiligenceState,
) -> Dict[str, Any]:
    try:
        controller.begin_workflow()
        updates = controller.retrieve_data()
        controller.persist_state(
            _state_snapshot(state, updates),
            "data_retrieval",
            status=WorkflowStatus.RUNNING,
        )
        return updates
    except Exception as exc:
        error = str(exc)
        updates = {"error_details": error}
        controller.persist_state(
            _state_snapshot(state, updates),
            "data_retrieval",
            status=WorkflowStatus.RUNNING,
            error_details=error,
        )
        return updates


def _controller_node(
    controller: ControllerAgent,
    state: DueDiligenceState,
) -> Dict[str, Any]:
    try:
        updates = controller.prepare_controller()
        updates.update(
            {
                "workflow_status": WorkflowStatus.RUNNING.value,
                "current_step": "specialists",
            }
        )
        controller.persist_state(
            _state_snapshot(state, updates),
            "controller",
            status=WorkflowStatus.RUNNING,
        )
        return updates
    except Exception as exc:
        error = str(exc)
        updates = {"error_details": error}
        controller.persist_state(
            _state_snapshot(state, updates),
            "controller",
            status=WorkflowStatus.RUNNING,
            error_details=error,
        )
        return updates


async def _specialist_node(
    controller: ControllerAgent,
    agent_key: str,
    state: DueDiligenceState,
) -> Dict[str, Any]:
    updates = await controller.run_specialist(agent_key, state)
    controller.save_checkpoint(
        f"state:{agent_key}",
        _state_snapshot(state, updates),
    )
    return updates


def _aggregate_node(
    controller: ControllerAgent,
    state: DueDiligenceState,
) -> Dict[str, Any]:
    try:
        updates = controller.aggregate(state)
        aggregation = updates.get("aggregation") or {}
        if not aggregation.get("completed_agents"):
            updates["error_details"] = (
                "All specialist agents failed after their retry limits."
            )
        controller.persist_state(
            _state_snapshot(state, updates),
            "aggregation",
            status=WorkflowStatus.RUNNING,
        )
        return updates
    except Exception as exc:
        error = str(exc)
        updates = {"error_details": error}
        controller.persist_state(
            _state_snapshot(state, updates),
            "aggregation",
            status=WorkflowStatus.RUNNING,
            error_details=error,
        )
        return updates


async def _verification_node(
    controller: ControllerAgent,
    state: DueDiligenceState,
) -> Dict[str, Any]:
    try:
        updates = await controller.run_verification(state)
        controller.persist_state(
            _state_snapshot(state, updates),
            "verification",
            status=WorkflowStatus.RUNNING,
        )
        return updates
    except Exception as exc:
        error = str(exc)
        updates = {"verification_error": error}
        controller.persist_state(
            _state_snapshot(state, updates),
            "verification",
            status=WorkflowStatus.RUNNING,
            error_details=error,
        )
        return updates


async def _report_node(
    controller: ControllerAgent,
    state: DueDiligenceState,
) -> Dict[str, Any]:
    try:
        updates = await controller.generate_report(state)
        controller.persist_state(
            _state_snapshot(state, updates),
            "completed",
            status=WorkflowStatus.COMPLETED,
            report=updates.get("report"),
        )
        return updates
    except Exception as exc:
        error = str(exc)
        updates = {
            "workflow_status": WorkflowStatus.FAILED.value,
            "current_step": "report_failed",
            "error_details": error,
        }
        controller.persist_state(
            _state_snapshot(state, updates),
            "report_failed",
            status=WorkflowStatus.RUNNING,
            error_details=error,
        )
        return updates


def _failure_node(
    controller: ControllerAgent,
    state: DueDiligenceState,
) -> Dict[str, Any]:
    error = (
        state.get("error_details")
        or state.get("verification_error")
        or "Workflow failed."
    )
    return controller.fail_workflow(str(error))


def route_after_retrieval(state: DueDiligenceState) -> str:
    return "fail_workflow" if state.get("error_details") else "controller"


def route_after_controller(state: DueDiligenceState):
    if state.get("error_details"):
        return "fail_workflow"
    return ["financial", "marketing", "legal"]


def route_after_aggregate(state: DueDiligenceState) -> str:
    if state.get("error_details"):
        return "fail_workflow"
    return "verify_evidence"


def route_after_verification(state: DueDiligenceState) -> str:
    if state.get("verification_error"):
        return "fail_workflow"
    return "generate_report"


def route_after_report(state: DueDiligenceState) -> str:
    if state.get("workflow_status") == WorkflowStatus.COMPLETED.value:
        return "end"
    return "fail_workflow"


def build_due_diligence_graph(
    controller: ControllerAgent,
    *,
    checkpointer: Optional[MemorySaver] = None,
):
    graph = StateGraph(DueDiligenceState)

    graph.add_node(
        "data_retrieval",
        lambda state: _retrieval_node(controller, state),
    )
    graph.add_node(
        "controller",
        lambda state: _controller_node(controller, state),
    )
    async def financial_node(state: DueDiligenceState):
        return await _specialist_node(controller, "financial", state)

    async def marketing_node(state: DueDiligenceState):
        return await _specialist_node(controller, "marketing", state)

    async def legal_node(state: DueDiligenceState):
        return await _specialist_node(controller, "legal", state)

    async def verification_node(state: DueDiligenceState):
        return await _verification_node(controller, state)

    async def report_node(state: DueDiligenceState):
        return await _report_node(controller, state)

    graph.add_node("financial", financial_node)
    graph.add_node("marketing", marketing_node)
    graph.add_node("legal", legal_node)
    graph.add_node(
        "aggregate",
        lambda state: _aggregate_node(controller, state),
    )
    graph.add_node("verify_evidence", verification_node)
    graph.add_node("generate_report", report_node)
    graph.add_node(
        "fail_workflow",
        lambda state: _failure_node(controller, state),
    )

    graph.add_edge(START, "data_retrieval")
    graph.add_conditional_edges(
        "data_retrieval",
        route_after_retrieval,
        {
            "controller": "controller",
            "fail_workflow": "fail_workflow",
        },
    )
    graph.add_conditional_edges(
        "controller",
        route_after_controller,
        ["financial", "marketing", "legal", "fail_workflow"],
    )
    graph.add_edge("financial", "aggregate")
    graph.add_edge("marketing", "aggregate")
    graph.add_edge("legal", "aggregate")
    graph.add_conditional_edges(
        "aggregate",
        route_after_aggregate,
        {
            "verify_evidence": "verify_evidence",
            "fail_workflow": "fail_workflow",
        },
    )
    graph.add_conditional_edges(
        "verify_evidence",
        route_after_verification,
        {
            "generate_report": "generate_report",
            "fail_workflow": "fail_workflow",
        },
    )
    graph.add_conditional_edges(
        "generate_report",
        route_after_report,
        {
            "end": END,
            "fail_workflow": "fail_workflow",
        },
    )
    graph.add_edge("fail_workflow", END)

    return graph.compile(checkpointer=checkpointer)


async def run_due_diligence_workflow(
    workflow_id: int,
    db: Session,
    *,
    retry_limit: Optional[int] = None,
    retry_backoff_seconds: float = 0.05,
    max_pages: int = 5,
) -> Dict[str, Any]:
    workflow = db.get(DueDiligenceWorkflow, workflow_id)
    if workflow is None:
        raise LookupError(f"Workflow {workflow_id} was not found.")

    controller = ControllerAgent(
        db,
        workflow,
        retry_limit=retry_limit,
        retry_backoff_seconds=retry_backoff_seconds,
        max_pages=max_pages,
    )
    graph = build_due_diligence_graph(
        controller,
        checkpointer=MemorySaver(),
    )
    initial_state: DueDiligenceState = {
        "workflow_id": workflow.id,
        "analysis_id": workflow.analysis_id,
        "workflow_status": workflow.status,
        "current_step": workflow.current_step or "pending",
        "specialist_outputs": {},
        "specialist_errors": {},
        "attempts": {},
    }
    config = {
        "configurable": {
            "thread_id": f"due-diligence-workflow-{workflow.id}",
        }
    }
    return await graph.ainvoke(initial_state, config=config)
