import asyncio
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple, Type

from sqlalchemy.orm import Session

from app.agents.base import BaseAgent
from app.agents.financial import FinancialAgent
from app.agents.legal import LegalAgent
from app.agents.marketing import MarketingAgent
from app.agents.output import AgentOutput
from app.data.evidence_store import EvidenceStore
from app.db.models import Analysis, Startup


class AnalysisNotFoundError(LookupError):
    pass


class AgentNotFoundError(LookupError):
    pass


class InvalidAnalysisError(ValueError):
    pass


@dataclass(frozen=True)
class AgentDefinition:
    key: str
    name: str
    description: str
    agent_class: Type[BaseAgent]
    aliases: Tuple[str, ...] = ()


@dataclass(frozen=True)
class AgentRunResult:
    analysis_id: int
    startup_id: int
    outputs: List[AgentOutput]


AGENT_DEFINITIONS: Tuple[AgentDefinition, ...] = (
    AgentDefinition(
        key="financial",
        name="Financial Agent",
        description=(
            "Assesses funding, revenue, profitability, cash flow, debt, and "
            "financial risks."
        ),
        agent_class=FinancialAgent,
        aliases=("financial_analysis_agent",),
    ),
    AgentDefinition(
        key="marketing",
        name="Marketing Agent",
        description=(
            "Assesses market conditions, customers, competitors, positioning, "
            "and growth opportunities."
        ),
        agent_class=MarketingAgent,
        aliases=("market_analysis_agent",),
    ),
    AgentDefinition(
        key="legal",
        name="Legal Agent",
        description=(
            "Assesses registration, compliance, contracts, intellectual "
            "property, and legal records."
        ),
        agent_class=LegalAgent,
        aliases=("legal_compliance_agent",),
    ),
)

_AGENT_BY_KEY: Dict[str, AgentDefinition] = {
    definition.key: definition for definition in AGENT_DEFINITIONS
}
_AGENT_BY_ALIAS: Dict[str, AgentDefinition] = {
    alias: definition
    for definition in AGENT_DEFINITIONS
    for alias in definition.aliases
}


def available_agents() -> List[AgentDefinition]:
    return list(AGENT_DEFINITIONS)


def resolve_agent(agent_key: str) -> AgentDefinition:
    normalised = (agent_key or "").strip().lower()
    definition = _AGENT_BY_KEY.get(normalised) or _AGENT_BY_ALIAS.get(
        normalised
    )
    if definition is None:
        supported = ", ".join(definition.key for definition in AGENT_DEFINITIONS)
        raise AgentNotFoundError(
            f"Unknown agent '{agent_key}'. Supported agents: {supported}."
        )
    return definition


class AgentOrchestrator:
    def __init__(self, db: Session) -> None:
        self.db = db

    async def run(
        self,
        analysis_id: int,
        agent_keys: Optional[Sequence[str]] = None,
    ) -> AgentRunResult:
        analysis = self._analysis(analysis_id)
        startup = self._startup(analysis)
        definitions = self._definitions(agent_keys)

        async def _run_one(definition: AgentDefinition) -> AgentOutput:
            agent = definition.agent_class(self.db)
            return await agent.execute(
                startup.id,
                {"analysis_id": analysis.id},
            )

        outputs = list(
            await asyncio.gather(*(_run_one(definition) for definition in definitions))
        )

        return AgentRunResult(
            analysis_id=analysis.id,
            startup_id=startup.id,
            outputs=outputs,
        )

    async def run_one(
        self,
        analysis_id: int,
        agent_key: str,
    ) -> AgentRunResult:
        return await self.run(analysis_id, [agent_key])

    def _analysis(self, analysis_id: int) -> Analysis:
        analysis = self.db.get(Analysis, analysis_id)
        if analysis is None:
            raise AnalysisNotFoundError(
                f"Analysis {analysis_id} was not found."
            )
        return analysis

    def _startup(self, analysis: Analysis) -> Startup:
        try:
            return EvidenceStore(self.db).ensure_startup(
                analysis.startup_name,
                analysis.website,
                industry=analysis.industry,
                user_id=analysis.user_id,
            )
        except ValueError as exc:
            raise InvalidAnalysisError(str(exc)) from exc

    def _definitions(
        self,
        agent_keys: Optional[Sequence[str]],
    ) -> List[AgentDefinition]:
        if not agent_keys:
            return list(AGENT_DEFINITIONS)

        definitions: List[AgentDefinition] = []
        seen = set()
        for agent_key in agent_keys:
            definition = resolve_agent(agent_key)
            if definition.key in seen:
                continue
            seen.add(definition.key)
            definitions.append(definition)
        return definitions
