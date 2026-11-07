from enum import Enum
from typing import Dict, List, Optional

import uuid
from pydantic import BaseModel, Field, model_validator
from typing import Optional


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
    CONFLICTING = "CONFLICTING"


class ExecutionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"


class AssessmentStatus(str, Enum):
    COMPLETED = "completed"
    INSUFFICIENT_INFORMATION = "insufficient_information"
    FAILED = "failed"


class EvidenceReference(BaseModel):
    evidence_id: int
    source_url: str
    source_title: str
    source_category: str
    verification_status: EvidenceStatus
    excerpt: str


class AgentFinding(BaseModel):
    finding_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    category: Optional[str] = None
    claim: Optional[str] = None
    finding: Optional[str] = None
    dimension: Optional[str] = None
    summary: Optional[str] = None
    explanation: Optional[str] = None
    risk_level: RiskLevel = RiskLevel.UNKNOWN
    evidence_status: EvidenceStatus = EvidenceStatus.UNAVAILABLE
    evidence_references: List[int] = Field(default_factory=list)
    source_ids: List[int] = Field(default_factory=list)
    investor_impact: Optional[str] = None

    @model_validator(mode="after")
    def _normalise_shared_fields(self):
        if self.category is None and self.dimension is not None:
            self.category = self.dimension
        if self.dimension is None and self.category is not None:
            self.dimension = self.category
        if self.claim is None and self.summary is not None:
            self.claim = self.summary
        if self.summary is None and self.claim is not None:
            self.summary = self.claim
        if self.finding is None and self.claim is not None:
            self.finding = self.claim
        if self.claim is None and self.finding is not None:
            self.claim = self.finding
        if not self.source_ids and self.evidence_references:
            self.source_ids = list(self.evidence_references)
        if not self.evidence_references and self.source_ids:
            self.evidence_references = list(self.source_ids)
        if self.investor_impact is None:
            self.investor_impact = ""
        if self.explanation is None:
            self.explanation = ""
        return self


class AgentOutput(BaseModel):
    agent_name: str = ""
    analysis_id: int = 0
    findings: List[AgentFinding] = Field(default_factory=list)
    detailed_explanations: Dict[str, str] = Field(default_factory=dict)
    evidence_references: List[EvidenceReference] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.UNKNOWN
    risk_levels: Dict[str, RiskLevel] = Field(default_factory=dict)
    evidence_status: EvidenceStatus = EvidenceStatus.UNAVAILABLE
    investor_impact: str = ""
    missing_information: List[str] = Field(default_factory=list)
    execution_status: ExecutionStatus = ExecutionStatus.SUCCESS
    status: Optional[str] = None
    assessment_status: Optional[str] = None
    error_details: Optional[str] = None

    @model_validator(mode="after")
    def _normalise_assessment_status(self):
        if self.status is None:
            self.status = self._assessment_value(self.execution_status)
        if self.assessment_status is None:
            self.assessment_status = self.status
        if self.status is None:
            self.status = self.assessment_status
        return self

    @staticmethod
    def _assessment_value(value: ExecutionStatus) -> str:
        mapping = {
            ExecutionStatus.SUCCESS: "completed",
            ExecutionStatus.COMPLETED: "completed",
            ExecutionStatus.PARTIAL: "insufficient_information",
            ExecutionStatus.INSUFFICIENT_INFORMATION: "insufficient_information",
            ExecutionStatus.FAILED: "failed",
        }
        return mapping.get(value, str(value).lower())
