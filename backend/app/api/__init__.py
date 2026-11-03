from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.data import (
    Cache,
    EvidenceStore,
    PublicDataRetriever,
    UnsafeURLError,
)
from app.db.models import Analysis
from app.db.session import get_db
from app.schemas import (
    AnalysisCreate,
    AnalysisOut,
    EvidenceCollectionOut,
    EvidenceOut,
    EvidenceSearchResponse,
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
