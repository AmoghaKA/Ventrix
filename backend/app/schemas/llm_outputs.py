from pydantic import BaseModel, Field
from typing import List, Optional


class ControllerOutput(BaseModel):
    startup_name: str
    summary: str
    key_risks: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)


class FinancialOutput(BaseModel):
    revenue_summary: Optional[str] = None
    profitability: Optional[str] = None
    risks: List[str] = Field(default_factory=list)


class AgentLLMResult(BaseModel):
    agent_name: str
    provider: str
    parsed: dict
