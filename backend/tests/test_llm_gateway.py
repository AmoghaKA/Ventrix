"""Tests for the backend LLM gateway."""

import unittest

from app.llm.gateway import LLMGateway, LLMProvider, LLMProviderError


class LLMGatewayTests(unittest.TestCase):
    def test_fallback_order_and_usage_tracking(self):
        calls = []

        def first_generate(prompt, provider):
            calls.append(provider.name)
            raise RuntimeError("primary failed")

        def second_generate(prompt, provider):
            calls.append(provider.name)
            return type("Response", (), {
                "provider": provider.name,
                "model": provider.model,
                "text": "ok",
                "latency_ms": 0.0,
                "metadata": {},
            })()

        gateway = LLMGateway(
            providers=[
                LLMProvider("Gemini", "gemini", "key", 1, first_generate),
                LLMProvider("Mistral", "mistral", "key", 2, second_generate),
            ]
        )

        response = gateway.generate("hello")

        self.assertEqual(response.text, "ok")
        self.assertEqual(calls, ["Gemini", "Mistral"])
        self.assertEqual(gateway.usage()["Mistral"], 1)
        self.assertEqual(gateway.usage()["Gemini"], 0)
        self.assertEqual(len(gateway.fallback_history()), 1)
        self.assertEqual(gateway.fallback_history()[0]["from_provider"], "Gemini")

    def test_unconfigured_provider_is_skipped(self):
        def generate(prompt, provider):
            return type("Response", (), {
                "provider": provider.name,
                "model": provider.model,
                "text": "ok",
                "latency_ms": 0.0,
                "metadata": {},
            })()

        gateway = LLMGateway(
            providers=[
                LLMProvider("Gemini", "gemini", "", 1, generate),
                LLMProvider("Mistral", "mistral", "key", 2, generate),
            ]
        )

        response = gateway.generate("hello")

        self.assertEqual(response.provider, "Mistral")
        self.assertTrue(any(item["reason"] == "not_configured" for item in gateway.fallback_history()))

    def test_all_providers_fail(self):
        def generate(prompt, provider):
            raise RuntimeError("boom")

        gateway = LLMGateway(
            providers=[
                LLMProvider("Gemini", "gemini", "key", 1, generate),
            ]
        )

        with self.assertRaises(LLMProviderError):
            gateway.generate("hello")

    def test_empty_prompt_rejected(self):
        gateway = LLMGateway(providers=[])
        with self.assertRaises(ValueError):
            gateway.generate("   ")


if __name__ == "__main__":
    unittest.main()
