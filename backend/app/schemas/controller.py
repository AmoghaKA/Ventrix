from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StartupInput(BaseModel):
    startup_name: str = Field(..., min_length=1)
    website: str = Field(..., min_length=1)
    country: Optional[str] = None
    industry: Optional[str] = None
    additional_information: Optional[str] = None


class AgentResult(BaseModel):
    agent_key: str
    agent_name: str
    status: str = Field(..., pattern="^(completed|insufficient_information|failed)$")
    output: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class VerificationResult(BaseModel):
    status: str = Field(..., pattern="^(completed|insufficient_information|failed)$")
    verification_status: Optional[str] = None
    result: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class ControllerAssessment(BaseModel):
    summary: str
    key_risks: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    recommended_next_steps: List[str] = Field(default_factory=list)


class ControllerResponse(BaseModel):
    analysis_id: str
    startup: StartupInput
    status: str = Field(..., pattern="^(pending|running|completed|failed)$")
    agent_results: List[AgentResult] = Field(default_factory=list)
    verification_result: Optional[VerificationResult] = None
    consolidated_findings: Dict[str, Any] = Field(default_factory=dict)
    controller_assessment: Optional[ControllerAssessment] = None
    errors: List[str] = Field(default_factory=list)
