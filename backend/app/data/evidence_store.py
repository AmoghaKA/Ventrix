from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.data.extraction import extract_source
from app.data.retrieval import RetrievalReport
from app.db.models import Analysis, Evidence, Startup


@dataclass
class StoreResult:
    total_sources: int = 0
    stored: int = 0
    updated: int = 0
    skipped: int = 0


@dataclass
class SearchResult:
    total: int
    items: List[Evidence]


def canonical_website(website: str) -> str:
    value = (website or "").strip()
    if not value:
        raise ValueError("A website URL is required")
    if "://" not in value:
        value = f"https://{value}"

    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError("A valid http or https website URL is required")
    if parsed.username or parsed.password:
        raise ValueError("Website URLs containing credentials are not supported")

    host = parsed.hostname.lower()
    host = f"[{host}]" if ":" in host else host
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("The website URL contains an invalid port") from exc

    netloc = f"{host}:{port}" if port else host
    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme.lower(), netloc, path, "", ""))


class EvidenceStore:
    def __init__(self, db: Session) -> None:
        self.db = db

    def ensure_startup(
        self,
        name: str,
        website: str,
        *,
        industry: Optional[str] = None,
    ) -> Startup:
        canonical = canonical_website(website)
        startup = (
            self.db.query(Startup)
            .filter(Startup.website == canonical)
            .one_or_none()
        )

        if startup is None:
            startup = Startup(
                name=name.strip(),
                website=canonical,
                industry=industry.strip() if industry else None,
            )
            self.db.add(startup)
            self.db.flush()
            return startup

        if industry and not startup.industry:
            startup.industry = industry.strip()
            self.db.flush()

        return startup

    def store_report(
        self,
        analysis: Analysis,
        startup: Startup,
        report: RetrievalReport,
    ) -> StoreResult:
        result = StoreResult(total_sources=len(report.sources))

        for source in report.sources:
            extracted = extract_source(source)
            if extracted is None:
                result.skipped += 1
                continue

            source_url = (source.final_url or source.url).strip()
            existing = (
                self.db.query(Evidence)
                .filter(
                    Evidence.analysis_id == analysis.id,
                    Evidence.source_url == source_url,
                )
                .one_or_none()
            )

            if existing is None:
                evidence = Evidence(
                    startup_id=startup.id,
                    analysis_id=analysis.id,
                    source_url=source_url,
                    source_title=extracted.source_title,
                    source_category=extracted.source_category,
                    extracted_information=extracted.extracted_information,
                    raw_text=extracted.raw_text,
                    publication_date=extracted.publication_date,
                    verification_status="unverified",
                    related_agent=extracted.related_agent,
                    findings=extracted.findings,
                    source_metadata=extracted.source_metadata,
                    content_hash=extracted.content_hash,
                )
                self.db.add(evidence)
                result.stored += 1
            else:
                content_changed = existing.content_hash != extracted.content_hash
                existing.startup_id = startup.id
                existing.source_title = extracted.source_title
                existing.source_category = extracted.source_category
                existing.extracted_information = extracted.extracted_information
                existing.raw_text = extracted.raw_text
                existing.publication_date = extracted.publication_date
                existing.retrieval_date = datetime.utcnow()
                existing.related_agent = extracted.related_agent
                existing.findings = extracted.findings
                existing.source_metadata = extracted.source_metadata
                existing.content_hash = extracted.content_hash
                if content_changed:
                    existing.verification_status = "unverified"
                result.updated += 1

        self.db.flush()
        return result

    def get(self, evidence_id: int) -> Optional[Evidence]:
        return self.db.get(Evidence, evidence_id)

    def search(
        self,
        *,
        analysis_id: Optional[int] = None,
        startup_id: Optional[int] = None,
        query: Optional[str] = None,
        category: Optional[str] = None,
        verification_status: Optional[str] = None,
        related_agent: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> SearchResult:
        filters = []
        if analysis_id is not None:
            filters.append(Evidence.analysis_id == analysis_id)
        if startup_id is not None:
            filters.append(Evidence.startup_id == startup_id)
        if category:
            filters.append(Evidence.source_category == category)
        if verification_status:
            filters.append(Evidence.verification_status == verification_status)
        if related_agent:
            filters.append(Evidence.related_agent == related_agent)
        if query and query.strip():
            term = f"%{query.strip()}%"
            filters.append(
                or_(
                    Evidence.source_title.ilike(term),
                    Evidence.source_url.ilike(term),
                    Evidence.extracted_information.ilike(term),
                    Evidence.raw_text.ilike(term),
                )
            )

        base_query = self.db.query(Evidence)
        if filters:
            base_query = base_query.filter(*filters)

        total = base_query.count()
        items = (
            base_query.order_by(
                Evidence.retrieval_date.desc(),
                Evidence.id.desc(),
            )
            .offset(offset)
            .limit(limit)
            .all()
        )
        return SearchResult(total=total, items=items)
