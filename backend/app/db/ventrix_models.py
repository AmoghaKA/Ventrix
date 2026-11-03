import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.types import UUID, JSON as JSONB

VentrixBase = declarative_base()


def _now():
    return datetime.now(timezone.utc)


class Startup(VentrixBase):
    __tablename__ = "startups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    website = Column(Text, nullable=True)
    industry = Column(String(120), nullable=True)
    stage = Column(String(64), nullable=True)
    location = Column(String(120), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class AnalysisRun(VentrixBase):
    __tablename__ = "analysis_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    startup_id = Column(UUID(as_uuid=True), ForeignKey("startups.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="pending")
    country = Column(String(120), nullable=True)
    industry = Column(String(120), nullable=True)
    additional_information = Column(Text, nullable=True)
    overall_assessment = Column(String(64), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

    __table_args__ = (
        CheckConstraint("status in ('pending','running','completed','failed')", name="ck_analysis_runs_status"),
    )


class AgentResult(VentrixBase):
    __tablename__ = "agent_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_key = Column(String(64), nullable=False, index=True)
    agent_name = Column(String(128), nullable=False)
    status = Column(String(32), nullable=False, default="completed")
    output = Column(JSONB, nullable=False, default=dict)
    confidence_score = Column(Numeric(5, 4), nullable=True)
    error_details = Column(Text, nullable=True)
    attempt_count = Column(Integer, nullable=False, default=1)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

    __table_args__ = (
        CheckConstraint("status in ('completed','insufficient_information','failed')", name="ck_agent_results_status"),
    )


class Evidence(VentrixBase):
    __tablename__ = "evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    startup_id = Column(UUID(as_uuid=True), ForeignKey("startups.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    source_url = Column(Text, nullable=False)
    source_title = Column(String(512), nullable=False, default="")
    source_category = Column(String(32), nullable=False, index=True)
    extracted_information = Column(Text, nullable=False)
    raw_text = Column(Text, nullable=True)
    publication_date = Column(DateTime(timezone=True), nullable=True)
    retrieval_date = Column(DateTime(timezone=True), nullable=False, default=_now)
    verification_status = Column(String(32), nullable=False, default="unverified", index=True)
    related_agent = Column(String(64), nullable=False, index=True)
    findings = Column(JSONB, nullable=False, default=list)
    source_metadata = Column(JSONB, nullable=False, default=dict)
    content_hash = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

    __table_args__ = (
        UniqueConstraint("analysis_run_id", "source_url", name="uq_evidence_analysis_source"),
    )


class VerificationResult(VentrixBase):
    __tablename__ = "verification_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="completed")
    verification_status = Column(String(64), nullable=True)
    result = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

    __table_args__ = (
        CheckConstraint("status in ('completed','insufficient_information','failed')", name="ck_verification_results_status"),
    )


class Report(VentrixBase):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_run_id = Column(UUID(as_uuid=True), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    startup_id = Column(UUID(as_uuid=True), ForeignKey("startups.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=True)
    overall_score = Column(Numeric(5, 2), nullable=True)
    recommendation = Column(Text, nullable=True)
    content = Column(JSONB, nullable=False, default=dict)
    file_path = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)


class UsageLimit(VentrixBase):
    __tablename__ = "usage_limits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope = Column(String(16), nullable=False)
    scope_id = Column(String(255), nullable=True)
    max_analyses = Column(Integer, nullable=False, default=10)
    used_analyses = Column(Integer, nullable=False, default=0)
    reserved_count = Column(Integer, nullable=False, default=0)
    period_start = Column(DateTime(timezone=True), nullable=True)
    period_end = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

    __table_args__ = (
        UniqueConstraint("scope", "scope_id", name="uq_usage_limits_scope"),
        CheckConstraint("scope in ('global','user')", name="ck_usage_limits_scope"),
    )
