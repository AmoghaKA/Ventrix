import httpx

from app.core.config import settings
from app.llm.providers.base import BaseLLMProvider, LLMProviderError


class GeminiProvider(BaseLLMProvider):
    name = "Google Gemini"

    def __init__(self, api_key: str = "", model: str = "", timeout_seconds: float = 30.0):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self.timeout_seconds = timeout_seconds or settings.LLM_TIMEOUT_SECONDS

    async def generate_text(self, prompt: str, response_schema=None) -> str:
        if not self.configured:
            raise LLMProviderError(f"{self.name} is not configured")
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:  # noqa: BLE001
            raise LLMProviderError(f"{self.name} request failed: {exc}") from exc

        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError(f"{self.name} returned an unexpected response") from exc
