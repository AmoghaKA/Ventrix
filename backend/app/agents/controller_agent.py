import asyncio
import logging
import uuid
from typing import Any, Awaitable, Callable, Dict, List, Optional

from app.llm.gateway import llm_gateway
from app.schemas.controller import (
    AgentResult,
    ControllerAssessment,
    ControllerResponse,
    StartupInput,
    VerificationResult,
)

logger = logging.getLogger("ventrix.controller")

SpecialistRunner = Callable[[StartupInput], Awaitable[AgentResult]]
VerificationRunner = Callable[[List[AgentResult]], Awaitable[VerificationResult]]
StatusUpdater = Callable[[str, str], Awaitable[None]]
RunCreator = Callable[[StartupInput], Awaitable[str]]


class ControllerAgent:
    def __init__(
        self,
        *,
        specialist_agents: Optional[Dict[str, SpecialistRunner]] = None,
        verification_agent: Optional[VerificationRunner] = None,
        status_updater: Optional[StatusUpdater] = None,
        run_creator: Optional[RunCreator] = None,
        llm_gateway_instance=llm_gateway,
    ) -> None:
        self.specialist_agents = specialist_agents or {}
        self.verification_agent = verification_agent
        self.status_updater = status_updater
        self.run_creator = run_creator
        self.llm = llm_gateway_instance

    async def _update_status(self, analysis_id: str, status: str) -> None:
        if self.status_updater is None:
            return
        try:
            await self.status_updater(analysis_id, status)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Status update failed for %s: %s", analysis_id, exc)

    async def _create_run(self, startup: StartupInput) -> str:
        if self.run_creator is not None:
            try:
                return await self.run_creator(startup)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Run creation failed: %s", exc)
        return str(uuid.uuid4())

    def _is_input_sufficient(self, startup: StartupInput) -> List[str]:
        missing = []
        if not startup.startup_name.strip():
            missing.append("startup_name")
        if not startup.website.strip():
            missing.append("website")
        return missing

    async def _run_specialist(self, key: str, runner: SpecialistRunner, startup: StartupInput) -> AgentResult:
        try:
            result = await runner(startup)
            if not isinstance(result, AgentResult):
                result = AgentResult.model_validate(result)
            return result
        except Exception as exc:  # noqa: BLE001
            logger.exception("Specialist agent %s failed", key)
            return AgentResult(
                agent_key=key,
                agent_name=key,
                status="failed",
                output={},
                error=str(exc),
            )

    async def run(self, startup: StartupInput, analysis_id: Optional[str] = None) -> ControllerResponse:
        try:
            startup = StartupInput.model_validate(startup)
        except Exception as exc:  # noqa: BLE001
            return ControllerResponse(
                analysis_id=analysis_id or str(uuid.uuid4()),
                startup=StartupInput.model_construct(startup_name="", website=""),
                status="failed",
                errors=[str(exc)],
            )
        missing_input = self._is_input_sufficient(startup)
        if missing_input:
            return ControllerResponse(
                analysis_id=analysis_id or str(uuid.uuid4()),
                startup=startup,
                status="failed",
                errors=[f"Insufficient startup input: {', '.join(missing_input)}"],
            )

        analysis_id = analysis_id or await self._create_run(startup)
        await self._update_status(analysis_id, "running")

        errors: List[str] = []
        agent_results: List[AgentResult] = []

        if self.specialist_agents:
            tasks = [
                self._run_specialist(key, runner, startup)
                for key, runner in self.specialist_agents.items()
            ]
            agent_results = list(await asyncio.gather(*tasks))

        for result in agent_results:
            if result.status == "failed" and result.error:
                errors.append(f"{result.agent_key}: {result.error}")

        verification_result: Optional[VerificationResult] = None
        if self.verification_agent is not None:
            try:
                verification_result = await self.verification_agent(agent_results)
                if not isinstance(verification_result, VerificationResult):
                    verification_result = VerificationResult.model_validate(verification_result)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Verification agent failed")
                errors.append(f"verification: {exc}")
                verification_result = VerificationResult(
                    status="failed",
                    error=str(exc),
                )

        consolidated = self._consolidate(agent_results, verification_result)

        assessment = await self._assess(startup, consolidated, errors)

        final_status = "completed" if not errors else "completed"
        if not agent_results and not verification_result:
            final_status = "completed"

        await self._update_status(analysis_id, final_status)

        return ControllerResponse(
            analysis_id=analysis_id,
            startup=startup,
            status=final_status,
            agent_results=agent_results,
            verification_result=verification_result,
            consolidated_findings=consolidated,
            controller_assessment=assessment,
            errors=errors,
        )

    def _consolidate(
        self,
        agent_results: List[AgentResult],
        verification_result: Optional[VerificationResult],
    ) -> Dict[str, Any]:
        consolidated: Dict[str, Any] = {
            "available_agents": [r.agent_key for r in agent_results if r.status == "completed"],
            "failed_agents": [r.agent_key for r in agent_results if r.status == "failed"],
            "insufficient_agents": [
                r.agent_key for r in agent_results if r.status == "insufficient_information"
            ],
            "agent_outputs": {r.agent_key: r.output for r in agent_results},
        }
        if verification_result is not None:
            consolidated["verification"] = verification_result.result
            consolidated["verification_status"] = verification_result.verification_status
        return consolidated

    async def _assess(
        self,
        startup: StartupInput,
        consolidated: Dict[str, Any],
        errors: List[str],
    ) -> ControllerAssessment:
        prompt = (
            "You are the VENTRIX Controller Agent. Summarize the due diligence inputs below. "
            "Do not fabricate financials, legal, market, or source data. Label unavailable information clearly.\n\n"
            f"Startup: {startup.model_dump_json()}\n"
            f"Consolidated findings: {consolidated}\n"
            f"Errors: {errors}\n"
        )
        try:
            result = await self.llm.generate(
                agent_name="Controller Agent",
                prompt=prompt,
                response_schema=ControllerAssessment,
            )
            if result.parsed is not None:
                return result.parsed
        except Exception as exc:  # noqa: BLE001
            logger.warning("Controller LLM assessment failed: %s", exc)

        return ControllerAssessment(
            summary="Controller assessment unavailable; specialist outputs retained for review.",
            key_risks=[],
            missing_information=errors or ["No additional information provided."],
            recommended_next_steps=["Review specialist agent outputs and evidence."],
        )
