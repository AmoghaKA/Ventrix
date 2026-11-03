from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from typing import Optional, List, Dict, Any


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
    source: str
    source_url: Optional[HttpUrl] = None
    title: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class EvidenceCreate(EvidenceBase):
    pass


class EvidenceOut(EvidenceBase):
    id: int
    created_at: datetime

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


class HealthCheck(BaseModel):
    status: str
    version: str
    database: str
