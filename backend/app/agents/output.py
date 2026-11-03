from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class EvidenceStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    UNAVAILABLE = "UNAVAILABLE"


class ExecutionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class EvidenceReference(BaseModel):
    evidence_id: int
    source_url: str
    source_title: str
    source_category: str
    verification_status: EvidenceStatus
    excerpt: str


class AgentFinding(BaseModel):
    dimension: str
    summary: str
    explanation: str
    risk_level: RiskLevel
    evidence_status: EvidenceStatus
    evidence_references: List[int] = Field(default_factory=list)
    investor_impact: str


class AgentOutput(BaseModel):
    agent_name: str
    analysis_id: int
    findings: List[AgentFinding] = Field(default_factory=list)
    detailed_explanations: Dict[str, str] = Field(default_factory=dict)
    evidence_references: List[EvidenceReference] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.UNKNOWN
    risk_levels: Dict[str, RiskLevel] = Field(default_factory=dict)
    evidence_status: EvidenceStatus = EvidenceStatus.UNAVAILABLE
    investor_impact: str
    missing_information: List[str] = Field(default_factory=list)
    execution_status: ExecutionStatus = ExecutionStatus.SUCCESS
    error_details: Optional[str] = None
