import asyncio
import unittest

from app.agents.controller_agent import ControllerAgent
from app.llm.gateway import LLMGateway
from app.schemas.controller import AgentResult, StartupInput, VerificationResult


class ControllerAgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_coordinates_agents_and_returns_results(self):
        async def financial(startup):
            return AgentResult(agent_key="financial", agent_name="Financial", status="completed", output={"revenue": "unknown"})

        async def marketing(startup):
            return AgentResult(agent_key="marketing", agent_name="Marketing", status="completed", output={})

        async def legal(startup):
            return AgentResult(agent_key="legal", agent_name="Legal", status="insufficient_information", output={}, error=None)

        async def verification(results):
            return VerificationResult(status="completed", verification_status="PARTIALLY_VERIFIED", result={"checked": len(results)})

        gateway = LLMGateway(providers=[], mock_mode=True)
        controller = ControllerAgent(
            specialist_agents={"financial": financial, "marketing": marketing, "legal": legal},
            verification_agent=verification,
            llm_gateway_instance=gateway,
        )

        startup = StartupInput(startup_name="Acme", website="https://acme.com")
        response = await controller.run(startup)

        self.assertEqual(response.status, "completed")
        self.assertEqual(len(response.agent_results), 3)
        self.assertEqual(response.verification_result.verification_status, "PARTIALLY_VERIFIED")
        self.assertIsNotNone(response.controller_assessment)

    async def test_handles_failed_agent(self):
        async def failing(startup):
            raise RuntimeError("boom")

        async def verification(results):
            return VerificationResult(status="completed", result={})

        gateway = LLMGateway(providers=[], mock_mode=True)
        controller = ControllerAgent(
            specialist_agents={"financial": failing},
            verification_agent=verification,
            llm_gateway_instance=gateway,
        )

        startup = StartupInput(startup_name="Acme", website="https://acme.com")
        response = await controller.run(startup)

        self.assertEqual(response.agent_results[0].status, "failed")
        self.assertTrue(any("financial" in e for e in response.errors))

    async def test_insufficient_input(self):
        gateway = LLMGateway(providers=[], mock_mode=True)
        controller = ControllerAgent(llm_gateway_instance=gateway)
        startup = StartupInput.model_construct(startup_name="", website="https://acme.com")
        response = await controller.run(startup)
        self.assertEqual(response.status, "failed")
        self.assertTrue(response.errors)


if __name__ == "__main__":
    unittest.main()
