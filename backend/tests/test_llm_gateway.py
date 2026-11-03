"""Tests for the backend LLM gateway."""

import asyncio
import unittest

from pydantic import BaseModel

from app.llm.gateway import LLMGateway, LLMProvider, LLMProviderError
from app.llm.providers.base import BaseLLMProvider


class SampleOutput(BaseModel):
    message: str


class FakeProvider(BaseLLMProvider):
    def __init__(self, name, configured=True, text="ok", error=None, priority=1):
        self.name = name
        self.model = name.lower()
        self.api_key = "key" if configured else ""
        self.priority = priority
        self.timeout_seconds = 1.0
        self._text = text
        self._error = error

    async def generate_text(self, prompt, response_schema=None):
        if self._error:
            raise self._error
        return self._text


class LLMGatewayTests(unittest.IsolatedAsyncioTestCase):
    async def test_fallback_order_and_usage_tracking(self):
        first = FakeProvider("Gemini", text="", error=RuntimeError("primary failed"))
        second = FakeProvider("Mistral", text='{"message":"ok"}')

        gateway = LLMGateway(providers=[first, second], mock_mode=False)

        response = await gateway.generate(
            agent_name="Test Agent",
            prompt="hello",
            response_schema=SampleOutput,
        )

        self.assertEqual(response.parsed.message, "ok")
        self.assertEqual(response.provider, "Mistral")
        self.assertEqual(gateway.usage()["Mistral"], 1)
        self.assertEqual(gateway.usage()["Gemini"], 0)
        self.assertEqual(len(gateway.fallback_history()), 1)

    async def test_unconfigured_provider_is_skipped(self):
        unconfigured = FakeProvider("Gemini", configured=False)
        configured = FakeProvider("Mistral", text='{"message":"ok"}')

        gateway = LLMGateway(providers=[unconfigured, configured], mock_mode=False)

        response = await gateway.generate(prompt="hello", response_schema=SampleOutput)

        self.assertEqual(response.provider, "Mistral")
        self.assertTrue(any(item["reason"] == "not_configured" for item in gateway.fallback_history()))

    async def test_all_providers_fail(self):
        provider = FakeProvider("Gemini", text="", error=RuntimeError("boom"))
        gateway = LLMGateway(providers=[provider], mock_mode=False)

        with self.assertRaises(LLMProviderError):
            await gateway.generate(prompt="hello", response_schema=SampleOutput)

    async def test_empty_prompt_rejected(self):
        gateway = LLMGateway(providers=[], mock_mode=False)
        with self.assertRaises(ValueError):
            await gateway.generate(prompt="   ")

    async def test_invalid_json_falls_back(self):
        bad = FakeProvider("Gemini", text="not json")
        good = FakeProvider("Mistral", text='{"message":"ok"}')
        gateway = LLMGateway(providers=[bad, good], mock_mode=False)

        response = await gateway.generate(prompt="hello", response_schema=SampleOutput)

        self.assertEqual(response.provider, "Mistral")

    async def test_mock_mode_runs_without_keys(self):
        gateway = LLMGateway(providers=[], mock_mode=True)
        response = await gateway.generate(
            agent_name="Controller Agent",
            prompt="hello",
            response_schema=SampleOutput,
        )
        self.assertEqual(response.provider, "Mock LLM")
        self.assertIsInstance(response.parsed, SampleOutput)


if __name__ == "__main__":
    unittest.main()
