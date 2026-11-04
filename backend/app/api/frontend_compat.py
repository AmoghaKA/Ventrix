from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Analysis, Startup
from app.db.session import get_db
from app.llm.gateway import llm_gateway
from typing import List

from app.db.models import WorkflowAgentStatus
from app.schemas import AnalysisCreate, AnalysisOut, StartupCreate, StartupOut
from app.services.usage_manager import UsageLimitManager
from app.db.session import SessionLocal
from app.workflows.service import create_workflow, require_latest_workflow, run_workflow_background
from app.workflows.status import WorkflowStatus

router = APIRouter(tags=["frontend-compat"])


@router.get("/health")
def health():
    return {"status": "healthy", "version": settings.APP_VERSION}


@router.post("/startup", response_model=StartupOut, status_code=201)
def create_startup(payload: StartupCreate, db: Session = Depends(get_db)):
    existing = db.query(Startup).filter(Startup.website == str(payload.website)).first()
    if existing is not None:
        return existing
    startup = Startup(
        name=payload.name.strip(),
        description=payload.description,
        website=str(payload.website),
        industry=payload.industry,
        stage=payload.stage,
        location=payload.location,
    )
    db.add(startup)
    db.commit()
    db.refresh(startup)
    return startup


@router.post("/analysis/start")
async def start_analysis(
    payload: AnalysisCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    manager = UsageLimitManager()
    if not manager.can_start_analysis(db):
        raise HTTPException(status_code=403, detail="Maximum analysis limit has been reached.")

    analysis = Analysis(
        startup_name=payload.startup_name.strip(),
        website=str(payload.website),
        country=payload.country.strip() if payload.country else None,
        industry=payload.industry.strip() if payload.industry else None,
        additional_information=(
            payload.additional_information.strip() if payload.additional_information else None
        ),
        status="pending",
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    db.commit()  # close transaction opened by refresh() before next usage-manager call

    manager.reserve_analysis(db)

    try:
        workflow = create_workflow(db, analysis.id, retry_limit=settings.WORKFLOW_MAX_RETRIES)
    except Exception:
        manager.complete_analysis(db, success=False)
        raise

    async def _run_and_finalize(workflow_id: int):
        await run_workflow_background(
            workflow_id,
            retry_limit=settings.WORKFLOW_MAX_RETRIES,
            max_pages=settings.WORKFLOW_MAX_PAGES,
        )
        db = SessionLocal()
        try:
            from app.db.models import DueDiligenceWorkflow

            final = db.get(DueDiligenceWorkflow, workflow_id)
            success = final is not None and final.status == WorkflowStatus.COMPLETED.value
            db.commit()
            UsageLimitManager().complete_analysis(db, success)
        finally:
            db.close()

    background_tasks.add_task(_run_and_finalize, workflow.id)
    return {"analysis_id": analysis.id, "status": "started"}


@router.get("/analysis/{analysis_id}/status")
def analysis_status(analysis_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    workflow = None
    try:
        workflow = require_latest_workflow(db, analysis_id)
    except Exception:
        workflow = None
    return {
        "analysis_id": analysis.id,
        "status": analysis.status,
        "workflow_status": workflow.status if workflow else None,
        "current_step": workflow.current_step if workflow else None,
        "error_details": workflow.error_details if workflow else None,
    }


@router.get("/analysis/{analysis_id}/results")
def analysis_results(analysis_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    workflow = require_latest_workflow(db, analysis_id)
    rows = (
        db.query(WorkflowAgentStatus)
        .filter(WorkflowAgentStatus.workflow_id == workflow.id)
        .order_by(WorkflowAgentStatus.sequence)
        .all()
    )
    return {
        "analysis_id": analysis_id,
        "workflow_status": workflow.status,
        "agent_statuses": [
            {
                "agent_key": row.agent_key,
                "agent_name": row.agent_name,
                "status": row.status,
                "output": row.output,
                "error_details": row.error_details,
            }
            for row in rows
        ],
    }


@router.get("/analysis/{analysis_id}/report")
def analysis_report(analysis_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    workflow = require_latest_workflow(db, analysis_id)
    if not workflow.report:
        raise HTTPException(status_code=404, detail="Report not available yet")
    return workflow.report


@router.get("/analysis/history", response_model=List[AnalysisOut])
def analysis_history(db: Session = Depends(get_db)):
    analyses = db.query(Analysis).order_by(Analysis.created_at.desc()).all()
    return analyses


@router.get("/system/usage")
def system_usage(db: Session = Depends(get_db)):
    return UsageLimitManager().get_usage(db)


@router.get("/system/providers")
def system_providers():
    return {
        "providers": llm_gateway.provider_status(),
        "active_provider": next(
            (p["name"] for p in llm_gateway.provider_status() if p.get("configured")),
            "Mock LLM" if settings.LLM_MOCK_MODE else "None",
        ),
    }
