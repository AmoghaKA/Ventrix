from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.db.session import Base


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
