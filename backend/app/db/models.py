import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    CheckConstraint,
)

from app.db.session import Base
from sqlalchemy.types import UUID


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    startup_name = Column(String(255), nullable=False)
    website = Column(String(2048), nullable=False)
    country = Column(String(120), nullable=True)
    industry = Column(String(120), nullable=True)
    additional_information = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="pending", index=True)
    overall_assessment = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class Startup(Base):
    __tablename__ = "startups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    website = Column(String(2048), nullable=False, unique=True, index=True)
    industry = Column(String(120), nullable=True)
    stage = Column(String(64), nullable=True)
    location = Column(String(120), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class Evidence(Base):
    __tablename__ = "evidence"
    __table_args__ = (
        UniqueConstraint(
            "analysis_id",
            "source_url",
            name="uq_evidence_analysis_source",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    startup_id = Column(
        Integer,
        ForeignKey("startups.id"),
        nullable=False,
        index=True,
    )
    analysis_id = Column(
        Integer,
        ForeignKey("analyses.id"),
        nullable=False,
        index=True,
    )
    source_url = Column(String(2048), nullable=False)
    source_title = Column(String(512), nullable=False, default="")
    source_category = Column(String(32), nullable=False, index=True)
    extracted_information = Column(Text, nullable=False)
    raw_text = Column(Text, nullable=True)
    publication_date = Column(DateTime, nullable=True)
    retrieval_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    verification_status = Column(
        String(32),
        nullable=False,
        default="unverified",
        index=True,
    )
    related_agent = Column(String(64), nullable=False, index=True)
    findings = Column(JSON, nullable=False, default=list)
    source_metadata = Column(JSON, nullable=False, default=dict)
    content_hash = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class DocumentExtractionFailure(Base):
    """Persisted processing failure; deliberately separate from evidence."""

    __tablename__ = "document_extraction_failures"
    __table_args__ = (
        UniqueConstraint(
            "analysis_id",
            "source_url",
            name="uq_document_extraction_failure_analysis_source",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    startup_id = Column(
        Integer,
        ForeignKey("startups.id"),
        nullable=False,
        index=True,
    )
    analysis_id = Column(
        Integer,
        ForeignKey("analyses.id"),
        nullable=False,
        index=True,
    )
    source_url = Column(String(2048), nullable=False)
    document_name = Column(String(512), nullable=True)
    failure_stage = Column(String(64), nullable=False)
    error_category = Column(String(64), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class RetrievalCacheEntry(Base):
    __tablename__ = "retrieval_cache"

    url = Column(String(2048), primary_key=True)
    final_url = Column(String(2048), nullable=True)
    status_code = Column(Integer, nullable=True)
    content_type = Column(String(255), nullable=True)
    content = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    extra = Column(JSON, nullable=False, default=dict)
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)


class DueDiligenceWorkflow(Base):
    __tablename__ = "due_diligence_workflows"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(
        Integer,
        ForeignKey("analyses.id"),
        nullable=False,
        index=True,
    )
    startup_id = Column(
        Integer,
        ForeignKey("startups.id"),
        nullable=True,
        index=True,
    )
    status = Column(
        String(32),
        nullable=False,
        default="PENDING",
        index=True,
    )
    current_step = Column(String(64), nullable=True)
    retry_limit = Column(Integer, nullable=False, default=2)
    error_details = Column(Text, nullable=True)
    state = Column(JSON, nullable=False, default=dict)
    report = Column(JSON, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class WorkflowAgentStatus(Base):
    __tablename__ = "workflow_agent_statuses"
    __table_args__ = (
        UniqueConstraint(
            "workflow_id",
            "agent_key",
            name="uq_workflow_agent_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(
        Integer,
        ForeignKey("due_diligence_workflows.id"),
        nullable=False,
        index=True,
    )
    analysis_id = Column(
        Integer,
        ForeignKey("analyses.id"),
        nullable=False,
        index=True,
    )
    agent_key = Column(String(64), nullable=False, index=True)
    agent_name = Column(String(128), nullable=False)
    sequence = Column(Integer, nullable=False, default=0)
    status = Column(
        String(32),
        nullable=False,
        default="PENDING",
        index=True,
    )
    attempt_count = Column(Integer, nullable=False, default=0)
    output = Column(JSON, nullable=True)
    error_details = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class WorkflowActivityLog(Base):
    __tablename__ = "workflow_activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(
        Integer,
        ForeignKey("due_diligence_workflows.id"),
        nullable=False,
        index=True,
    )
    analysis_id = Column(
        Integer,
        ForeignKey("analyses.id"),
        nullable=False,
        index=True,
    )
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    level = Column(String(16), nullable=False, default="INFO")
    event = Column(String(64), nullable=False)
    agent_key = Column(String(64), nullable=True, index=True)
    message = Column(Text, nullable=False)
    meta = Column(JSON, nullable=False, default=dict)


class WorkflowCheckpoint(Base):
    __tablename__ = "workflow_checkpoints"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(
        Integer,
        ForeignKey("due_diligence_workflows.id"),
        nullable=False,
        index=True,
    )
    step = Column(String(64), nullable=False)
    state = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


def _now_utc():
    return datetime.now(timezone.utc)


class UsageLimit(Base):
    __tablename__ = "usage_limits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope = Column(String(16), nullable=False)
    scope_id = Column(String(255), nullable=True)
    max_analyses = Column(Integer, nullable=False, default=10)
    used_analyses = Column(Integer, nullable=False, default=0)
    reserved_count = Column(Integer, nullable=False, default=0)
    period_start = Column(DateTime(timezone=True), nullable=True)
    period_end = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now_utc, onupdate=_now_utc)

    __table_args__ = (
        UniqueConstraint("scope", "scope_id", name="uq_usage_limits_scope"),
        CheckConstraint("scope in ('global','user')", name="ck_usage_limits_scope"),
    )
