import inspect
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, List, Optional

from pydantic import BaseModel

from app.core.config import settings
from app.llm.providers.base import BaseLLMProvider, LLMProviderError
from app.llm.providers.gemini import GeminiProvider
from app.llm.providers.groq import GroqProvider
from app.llm.providers.mistral import MistralProvider
from app.llm.providers.mock import MockProvider
from app.llm.providers.nvidia import NvidiaProvider

logger = logging.getLogger("ventrix.llm")


@dataclass
class LLMResponse:
    provider: str
    model: str
    text: str
    parsed: Any = None
    latency_ms: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class LLMProvider(BaseLLMProvider):
    """Backward-compatible provider wrapper."""

    name: str = ""
    model: str = ""
    api_key: str = ""
    priority: int = 0
    timeout_seconds: float = 30.0
    generate_fn: Any = None

    @property
    def configured(self) -> bool:
        return bool(self.api_key) or self.generate_fn is not None

    async def generate_text(self, prompt: str, response_schema=None) -> str:
        if self.generate_fn is None:
            raise LLMProviderError(f"{self.name} has no generate implementation")
        result = self.generate_fn(prompt, self)
        if inspect.isawaitable(result):
            result = await result
        if isinstance(result, str):
            return result
        if hasattr(result, "text"):
            return str(result.text)
        return str(result)


class LLMGateway:
    def __init__(
        self,
        providers: Optional[List[BaseLLMProvider]] = None,
        mock_mode: Optional[bool] = None,
        timeout_seconds: Optional[float] = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds or settings.LLM_TIMEOUT_SECONDS
        self.mock_mode = settings.LLM_MOCK_MODE if mock_mode is None else mock_mode

        if providers is None:
            providers = [
                GeminiProvider(timeout_seconds=self.timeout_seconds),
                NvidiaProvider(timeout_seconds=self.timeout_seconds),
                MistralProvider(timeout_seconds=self.timeout_seconds),
                GroqProvider(timeout_seconds=self.timeout_seconds),
            ]
            providers[0].priority = 1
            providers[1].priority = 2
            providers[2].priority = 3
            providers[3].priority = 4

        self._providers = sorted(providers, key=lambda p: getattr(p, "priority", 0))
        if self.mock_mode:
            self._providers = self._providers + [MockProvider(timeout_seconds=1.0)]
        self._lock = threading.RLock()
        self._usage = {getattr(p, "name", str(p)): 0 for p in self._providers}
        self._fallback_history: List[dict] = []

    @property
    def providers(self) -> List[BaseLLMProvider]:
        return list(self._providers)

    def provider_status(self) -> List[dict]:
        with self._lock:
            return [
                {
                    "name": getattr(p, "name", ""),
                    "model": getattr(p, "model", ""),
                    "configured": getattr(p, "configured", False),
                    "priority": getattr(p, "priority", 0),
                    "usage_count": self._usage.get(getattr(p, "name", ""), 0),
                }
                for p in self._providers
            ]

    def usage(self) -> dict:
        with self._lock:
            return dict(self._usage)

    def fallback_history(self) -> List[dict]:
        with self._lock:
            return [dict(item) for item in self._fallback_history]

    async def generate(
        self,
        prompt=None,
        *,
        agent_name: Optional[str] = None,
        response_schema: Optional[type[BaseModel]] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        if prompt is None:
            prompt = kwargs.pop("prompt", "")
        if agent_name is None:
            agent_name = kwargs.pop("agent_name", "LLM")
        if response_schema is None:
            response_schema = kwargs.pop("response_schema", None)

        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string")

        last_error: Optional[Exception] = None
        for index, provider in enumerate(self._providers):
            name = getattr(provider, "name", str(provider))
            model = getattr(provider, "model", "")
            if not getattr(provider, "configured", False):
                self._record_fallback(name, self._next_provider_name(index), "not_configured")
                continue
            try:
                started = time.perf_counter()
                text = await provider.generate_text(prompt, response_schema)
                latency_ms = (time.perf_counter() - started) * 1000
                parsed = None
                if response_schema is not None:
                    parsed = self._validate_json(text, response_schema)
                with self._lock:
                    self._usage[name] = self._usage.get(name, 0) + 1
                logger.info(
                    "LLM request completed agent=%s provider=%s model=%s latency_ms=%.2f",
                    agent_name,
                    name,
                    model,
                    latency_ms,
                )
                return LLMResponse(
                    provider=name,
                    model=model,
                    text=text,
                    parsed=parsed,
                    latency_ms=latency_ms,
                )
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning(
                    "LLM provider failed agent=%s provider=%s reason=%s",
                    agent_name,
                    name,
                    str(exc),
                )
                self._record_fallback(name, self._next_provider_name(index), str(exc))

        raise LLMProviderError(
            "All LLM providers failed: "
            + (str(last_error) if last_error else "no configured provider")
        )

    def _validate_json(self, text: str, schema: type[BaseModel]) -> Any:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise LLMProviderError(f"invalid JSON from LLM: {exc}") from exc
        try:
            return schema.model_validate(data)
        except Exception as exc:  # noqa: BLE001
            raise LLMProviderError(f"response did not match schema: {exc}") from exc

    def _next_provider_name(self, index: int) -> Optional[str]:
        for provider in self._providers[index + 1 :]:
            if getattr(provider, "configured", False):
                return getattr(provider, "name", None)
        for provider in self._providers[index + 1 :]:
            return getattr(provider, "name", None)
        return None

    def _record_fallback(self, from_provider: str, to_provider: Optional[str], reason: str) -> None:
        with self._lock:
            self._fallback_history.append(
                {
                    "from_provider": from_provider,
                    "to_provider": to_provider,
                    "reason": reason,
                    "timestamp": time.time(),
                }
            )


llm_gateway = LLMGateway()
