import httpx

from app.core.config import settings
from app.llm.providers.base import BaseLLMProvider, LLMProviderError


class MistralProvider(BaseLLMProvider):
    name = "Mistral"

    def __init__(self, api_key: str = "", model: str = "", timeout_seconds: float = 30.0):
        self.api_key = api_key or settings.MISTRAL_API_KEY
        self.model = model or settings.MISTRAL_MODEL
        self.timeout_seconds = timeout_seconds or settings.LLM_TIMEOUT_SECONDS

    async def generate_text(self, prompt: str, response_schema=None) -> str:
        if not self.configured:
            raise LLMProviderError(f"{self.name} is not configured")
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:  # noqa: BLE001
            raise LLMProviderError(f"{self.name} request failed: {exc}") from exc

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError(f"{self.name} returned an unexpected response") from exc
