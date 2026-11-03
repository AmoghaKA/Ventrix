from typing import List, Optional

from fastapi import (
    Response,
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Path,
    Query,
    status,
)
from sqlalchemy.orm import Session

from app.agents import (
    AgentNotFoundError,
    AgentOrchestrator,
    AgentOutput,
    AnalysisNotFoundError,
    InvalidAnalysisError,
    VerificationAgent,
    VerificationOutput,
    available_agents,
)
from app.agents.output import ExecutionStatus
from app.core.config import settings
from app.workflows.report import generate_report_pdf
from app.data import (
    Cache,
    EvidenceStore,
    PublicDataRetriever,
    UnsafeURLError,
)
from app.db.models import (
    Analysis,
    WorkflowActivityLog,
    WorkflowAgentStatus,
)
from app.db.session import get_db
from app.schemas import (
    AgentInfoOut,
    AgentRunOut,
    AnalysisCreate,
    AnalysisOut,
    EvidenceCollectionOut,
    EvidenceOut,
    EvidenceSearchResponse,
    WorkflowActivityLogOut,
    WorkflowAgentStatusOut,
    WorkflowOut,
)
from app.workflows.service import (
    WorkflowAlreadyRunningError,
    WorkflowNotFoundError,
    create_workflow,
    require_latest_workflow,
    run_workflow_background,
)

api_router = APIRouter()


@api_router.get("/health", tags=["health"])
async def api_health():
    return {"status": "ok"}


@api_router.post(
    "/analyses",
    response_model=AnalysisOut,
    status_code=status.HTTP_201_CREATED,
    tags=["analyses"],
)
def create_analysis(payload: AnalysisCreate, db: Session = Depends(get_db)):
    analysis = Analysis(
        startup_name=payload.startup_name.strip(),
        website=str(payload.website),
        country=payload.country.strip() if payload.country else None,
        industry=payload.industry.strip() if payload.industry else None,
        additional_information=(
            payload.additional_information.strip()
            if payload.additional_information
            else None
        ),
        status="pending",
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


@api_router.get("/analyses", response_model=List[AnalysisOut], tags=["analyses"])
def list_analyses(db: Session = Depends(get_db)):
    return db.query(Analysis).order_by(Analysis.created_at.desc()).all()


@api_router.get(
    "/analyses/{analysis_id}",
    response_model=AnalysisOut,
    tags=["analyses"],
)
def get_analysis(analysis_id: int, db: Session = Depends(get_db)):
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found",
        )
    return analysis


def _start_analysis_workflow(
    db: Session,
    background_tasks: BackgroundTasks,
    analysis_id: int,
    retry_limit: int,
    max_pages: int,
):
    try:
        workflow = create_workflow(
            db,
            analysis_id,
            retry_limit=retry_limit,
        )
    except WorkflowAlreadyRunningError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception:
        db.rollback()
        raise

    background_tasks.add_task(
        run_workflow_background,
        workflow.id,
        retry_limit=retry_limit,
        max_pages=max_pages,
    )
    return workflow


@api_router.post(
    "/analyses/{analysis_id}/start",
    response_model=WorkflowOut,
    status_code=status.HTTP_200_OK,
    tags=["workflows"],
)
async def start_analysis(
    background_tasks: BackgroundTasks,
    analysis_id: int = Path(..., ge=1),
    retry_limit: int = Query(
        settings.WORKFLOW_MAX_RETRIES,
        ge=0,
        le=5,
    ),
    max_pages: int = Query(settings.WORKFLOW_MAX_PAGES, ge=1, le=10),
    db: Session = Depends(get_db),
):
    return _start_analysis_workflow(
        db,
        background_tasks,
        analysis_id,
        retry_limit,
        max_pages,
    )


@api_router.post(
    "/analyses/{analysis_id}/workflow/start",
    response_model=WorkflowOut,
    status_code=status.HTTP_200_OK,
    tags=["workflows"],
    include_in_schema=False,
)
async def start_analysis_workflow_alias(
    background_tasks: BackgroundTasks,
    analysis_id: int = Path(..., ge=1),
    retry_limit: int = Query(
        settings.WORKFLOW_MAX_RETRIES,
        ge=0,
        le=5,
    ),
    max_pages: int = Query(settings.WORKFLOW_MAX_PAGES, ge=1, le=10),
    db: Session = Depends(get_db),
):
    return _start_analysis_workflow(
        db,
        background_tasks,
        analysis_id,
        retry_limit,
        max_pages,
    )


@api_router.get(
    "/analyses/{analysis_id}/workflow",
    response_model=WorkflowOut,
    tags=["workflows"],
)
def get_workflow_status(
    analysis_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    try:
        return require_latest_workflow(db, analysis_id)
    except WorkflowNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@api_router.get(
    "/analyses/{analysis_id}/workflow/status",
    response_model=WorkflowOut,
    tags=["workflows"],
    include_in_schema=False,
)
def get_workflow_status_alias(
    analysis_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    return get_workflow_status(analysis_id, db)


@api_router.get(
    "/analyses/{analysis_id}/workflow/agents",
    response_model=List[WorkflowAgentStatusOut],
    tags=["workflows"],
)
def get_workflow_agent_statuses(
    analysis_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    try:
        workflow = require_latest_workflow(db, analysis_id)
    except WorkflowNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return (
        db.query(WorkflowAgentStatus)
        .filter(WorkflowAgentStatus.workflow_id == workflow.id)
        .order_by(
            WorkflowAgentStatus.sequence,
            WorkflowAgentStatus.id,
        )
        .all()
    )


@api_router.get(
    "/analyses/{analysis_id}/workflow/logs",
    response_model=List[WorkflowActivityLogOut],
    tags=["workflows"],
)
def get_workflow_activity_logs(
    analysis_id: int = Path(..., ge=1),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    try:
        workflow = require_latest_workflow(db, analysis_id)
    except WorkflowNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return (
        db.query(WorkflowActivityLog)
        .filter(WorkflowActivityLog.workflow_id == workflow.id)
        .order_by(
            WorkflowActivityLog.timestamp,
            WorkflowActivityLog.id,
        )
        .offset(offset)
        .limit(limit)
        .all()
    )


async def _verify_analysis(
    db: Session,
    analysis_id: int,
) -> VerificationOutput:
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis {analysis_id} was not found.",
        )

    startup = None
    try:
        startup = EvidenceStore(db).ensure_startup(
            analysis.startup_name,
            analysis.website,
            industry=analysis.industry,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    orchestrator = AgentOrchestrator(db)
    result = await orchestrator.run(
        analysis.id,
        ["financial", "marketing", "legal"],
    )

    name_to_key = {
        "Financial Agent": "financial",
        "Marketing Agent": "marketing",
        "Legal Agent": "legal",
    }
    outputs_by_key: Dict[str, AgentOutput] = {}
    specialist_errors: Dict[str, str] = {}
    for output in result.outputs:
        key = name_to_key.get(output.agent_name)
        if key is None:
            continue
        outputs_by_key[key] = output
        if (
            output.execution_status == ExecutionStatus.FAILED
            or output.error_details
        ):
            specialist_errors[key] = (
                output.error_details or "Agent execution failed."
            )

    agent = VerificationAgent(db)
    return await agent.execute(
        startup.id,
        {
            "analysis_id": analysis.id,
            "specialist_outputs": outputs_by_key,
            "specialist_errors": specialist_errors,
        },
    )


@api_router.post(
    "/analyses/{analysis_id}/verify",
    response_model=VerificationOutput,
    tags=["verification"],
)
async def verify_analysis(
    analysis_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    return await _verify_analysis(db, analysis_id)


@api_router.post(
    "/analyses/{analysis_id}/verification/run",
    response_model=VerificationOutput,
    tags=["verification"],
    include_in_schema=False,
)
async def verify_analysis_run_alias(
    analysis_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    return await _verify_analysis(db, analysis_id)


@api_router.post(
    "/analyses/{analysis_id}/agents/verification/run",
    response_model=VerificationOutput,
    tags=["verification"],
    include_in_schema=False,
)
async def verify_analysis_agent_alias(
    analysis_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    return await _verify_analysis(db, analysis_id)


@api_router.get(
    "/analyses/{analysis_id}/verification",
    response_model=VerificationOutput,
    tags=["verification"],
)
def get_latest_verification(
    analysis_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    try:
        workflow = require_latest_workflow(db, analysis_id)
    except WorkflowNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    state = workflow.state or {}
    verification = state.get("verification")
    if not verification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No verification output is available for this analysis.",
        )
    try:
        return VerificationOutput.model_validate(verification)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc



@api_router.get(
    "/analyses/{analysis_id}/report",
    tags=["reports"],
)
def get_analysis_report(
    analysis_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    try:
        workflow = require_latest_workflow(db, analysis_id)
    except WorkflowNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    if not workflow.report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No report is available for this analysis.",
        )
    return workflow.report


@api_router.get(
    "/analyses/{analysis_id}/report/pdf",
    tags=["reports"],
)
def download_analysis_report_pdf(
    analysis_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    try:
        workflow = require_latest_workflow(db, analysis_id)
    except WorkflowNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    if not workflow.report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No report is available for this analysis.",
        )

    analysis = db.get(Analysis, analysis_id)
    pdf_bytes = generate_report_pdf(workflow.report, analysis=analysis)
    filename = f"ventrix-report-analysis-{analysis_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


@api_router.get(
    "/analyses/{analysis_id}/report/download",
    tags=["reports"],
    include_in_schema=False,
)
def download_analysis_report_pdf_alias(
    analysis_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
):
    return download_analysis_report_pdf(analysis_id, db)




@api_router.get("/system/status", tags=["system"])
def system_status(db: Session = Depends(get_db)):
    from app.core.config import settings

    analysis_count = db.query(Analysis).count()
    providers = []
    for name, env_name in (
        ("Gemini", "GEMINI_API_KEY"),
        ("NVIDIA Nemotron", "NVIDIA_API_KEY"),
        ("Mistral", "MISTRAL_API_KEY"),
    ):
        import os

        configured = bool(os.getenv(env_name))
        providers.append(
            {
                "name": name,
                "configured": configured,
                "active": False,
            }
        )
    active = "Not configured"
    for provider in providers:
        if provider["configured"]:
            active = provider["name"]
            provider["active"] = True
            break

    return {
        "api_status": "healthy",
        "database": "connected",
        "analysis_count": analysis_count,
        "max_analyses": 10,
        "providers": providers,
        "active_provider": active,
        "fallback_history": [],
        "version": "1.0.0",
    }


@api_router.get(
    "/agents",
    response_model=List[AgentInfoOut],
    tags=["agents"],
)
def list_agents():
    return [
        AgentInfoOut(
            key=definition.key,
            name=definition.name,
            description=definition.description,
        )
        for definition in available_agents()
    ]


@api_router.post(
    "/analyses/{analysis_id}/agents/run",
    response_model=AgentRunOut,
    tags=["agents"],
)
async def run_all_agents(
    analysis_id: int = Path(..., ge=1),
    agents: Optional[List[str]] = Query(None),
    db: Session = Depends(get_db),
):
    result = await _run_agents(db, analysis_id, agents)
    return AgentRunOut(
        analysis_id=result.analysis_id,
        startup_id=result.startup_id,
        outputs=result.outputs,
    )


@api_router.post(
    "/analyses/{analysis_id}/agents/{agent_key}/run",
    response_model=AgentOutput,
    tags=["agents"],
)
async def run_agent(
    analysis_id: int = Path(..., ge=1),
    agent_key: str = Path(..., min_length=1, max_length=64),
    db: Session = Depends(get_db),
):
    result = await _run_agents(db, analysis_id, [agent_key])
    return result.outputs[0]


async def _run_agents(
    db: Session,
    analysis_id: int,
    agent_keys: Optional[List[str]],
):
    try:
        result = await AgentOrchestrator(db).run(analysis_id, agent_keys)
        db.commit()
        return result
    except AnalysisNotFoundError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except AgentNotFoundError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidAnalysisError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception:
        db.rollback()
        raise


@api_router.post(
    "/analyses/{analysis_id}/collect-evidence",
    response_model=EvidenceCollectionOut,
    tags=["evidence"],
)
def collect_evidence(
    analysis_id: int,
    max_pages: int = Query(5, ge=1, le=10),
    db: Session = Depends(get_db),
):
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found",
        )

    store = EvidenceStore(db)
    startup = store.ensure_startup(
        analysis.startup_name,
        analysis.website,
        industry=analysis.industry,
    )

    retriever = PublicDataRetriever(
        cache=Cache(db),
        max_pages=max_pages,
    )
    try:
        report = retriever.retrieve(analysis.website, max_pages=max_pages)
    except UnsafeURLError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    try:
        result = store.store_report(analysis, startup, report)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return EvidenceCollectionOut(
        analysis_id=analysis.id,
        startup_id=startup.id,
        retrieved_sources=result.total_sources,
        stored_evidence=result.stored,
        updated_evidence=result.updated,
        skipped_sources=result.skipped,
        errors=[
            f"{failure.url}: {failure.reason}"
            for failure in report.failures
        ],
    )


@api_router.get(
    "/evidence",
    response_model=EvidenceSearchResponse,
    tags=["evidence"],
)
def search_evidence(
    analysis_id: Optional[int] = Query(None, ge=1),
    startup_id: Optional[int] = Query(None, ge=1),
    q: Optional[str] = Query(None, max_length=200),
    category: Optional[str] = Query(None, max_length=32),
    verification_status: Optional[str] = Query(None, max_length=32),
    related_agent: Optional[str] = Query(None, max_length=64),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    result = EvidenceStore(db).search(
        analysis_id=analysis_id,
        startup_id=startup_id,
        query=q,
        category=category,
        verification_status=verification_status,
        related_agent=related_agent,
        limit=limit,
        offset=offset,
    )
    return EvidenceSearchResponse(
        total=result.total,
        limit=limit,
        offset=offset,
        items=result.items,
    )


@api_router.get(
    "/evidence/{evidence_id}",
    response_model=EvidenceOut,
    tags=["evidence"],
)
def get_evidence(evidence_id: int, db: Session = Depends(get_db)):
    evidence = EvidenceStore(db).get(evidence_id)
    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found",
        )
    return evidence
