from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.agents.output import AgentOutput


class StartupBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    website: Optional[HttpUrl] = None
    industry: Optional[str] = None
    stage: Optional[str] = None
    location: Optional[str] = None


class StartupCreate(StartupBase):
    pass


class StartupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    website: Optional[HttpUrl] = None
    industry: Optional[str] = None
    stage: Optional[str] = None
    location: Optional[str] = None


class StartupOut(StartupBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EvidenceBase(BaseModel):
    startup_id: int
    analysis_id: int
    source_url: str
    source_title: str
    source_category: str
    extracted_information: str
    raw_text: Optional[str] = None
    publication_date: Optional[datetime] = None
    retrieval_date: datetime
    verification_status: str
    related_agent: str
    findings: List[Dict[str, Any]] = []
    source_metadata: Dict[str, Any] = {}
    content_hash: str


class EvidenceCreate(EvidenceBase):
    pass


class EvidenceOut(EvidenceBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EvidenceSearchResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[EvidenceOut]


class EvidenceCollectionOut(BaseModel):
    analysis_id: int
    startup_id: int
    retrieved_sources: int
    stored_evidence: int
    updated_evidence: int
    skipped_sources: int
    errors: List[str] = []


class AgentInfoOut(BaseModel):
    key: str
    name: str
    description: str


class AgentRunOut(BaseModel):
    analysis_id: int
    startup_id: int
    outputs: List[AgentOutput]


class WorkflowOut(BaseModel):
    id: int
    analysis_id: int
    startup_id: Optional[int] = None
    status: str
    current_step: Optional[str] = None
    retry_limit: int
    error_details: Optional[str] = None
    report: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WorkflowAgentStatusOut(BaseModel):
    id: int
    workflow_id: int
    analysis_id: int
    agent_key: str
    agent_name: str
    sequence: int
    status: str
    attempt_count: int
    output: Optional[Dict[str, Any]] = None
    error_details: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WorkflowActivityLogOut(BaseModel):
    id: int
    workflow_id: int
    analysis_id: int
    timestamp: datetime
    level: str
    event: str
    agent_key: Optional[str] = None
    message: str
    meta: Dict[str, Any] = {}

    class Config:
        from_attributes = True


class AgentOutputBase(BaseModel):
    startup_id: int
    agent_name: str
    output_type: str
    result: Dict[str, Any]
    confidence_score: Optional[float] = Field(None, ge=0, le=1)


class AgentOutputCreate(AgentOutputBase):
    pass


class AgentOutputOut(AgentOutputBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ReportBase(BaseModel):
    startup_id: int
    title: str
    summary: Optional[str] = None
    overall_score: Optional[float] = Field(None, ge=0, le=100)
    recommendation: Optional[str] = None
    content: Optional[Dict[str, Any]] = None


class ReportCreate(ReportBase):
    pass


class ReportOut(ReportBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AnalysisCreate(BaseModel):
    startup_name: str = Field(..., min_length=1, max_length=255)
    website: HttpUrl
    country: Optional[str] = Field(None, max_length=120)
    industry: Optional[str] = Field(None, max_length=120)
    additional_information: Optional[str] = Field(None, max_length=5000)


class AnalysisOut(BaseModel):
    id: int
    startup_name: str
    website: str
    country: Optional[str] = None
    industry: Optional[str] = None
    additional_information: Optional[str] = None
    status: str
    overall_assessment: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class HealthCheck(BaseModel):
    status: str
    version: str
    database: str

from app.agents.verification import VerificationOutput as VerificationOut
