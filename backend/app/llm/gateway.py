import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from app.core.config import settings


class LLMProviderError(Exception):
    """Raised when an LLM provider cannot complete a request."""


@dataclass
class LLMResponse:
    provider: str
    model: str
    text: str
    latency_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMProvider:
    name: str
    model: str
    api_key: str = ""
    priority: int = 0
    generate_fn: Optional[Callable[[str, "LLMProvider"], LLMResponse]] = None

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str) -> LLMResponse:
        if not self.configured:
            raise LLMProviderError(f"{self.name} is not configured")
        if self.generate_fn is not None:
            return self.generate_fn(prompt, self)
        raise LLMProviderError(f"{self.name} has no generate implementation")


class LLMGateway:
    """Backend-only provider router with automatic fallback."""

    def __init__(self, providers: Optional[List[LLMProvider]] = None) -> None:
        self._providers = sorted(
            providers if providers is not None else self._default_providers(),
            key=lambda provider: provider.priority,
        )
        self._lock = threading.RLock()
        self._usage: Dict[str, int] = {provider.name: 0 for provider in self._providers}
        self._fallback_history: List[Dict[str, Any]] = []

    @staticmethod
    def _default_providers() -> List[LLMProvider]:
        return [
            LLMProvider(
                name="Google Gemini",
                model="gemini-1.5-flash",
                api_key=settings.GEMINI_API_KEY,
                priority=1,
            ),
            LLMProvider(
                name="NVIDIA Nemotron",
                model="nvidia/nemotron-70b-instruct",
                api_key=settings.NVIDIA_API_KEY,
                priority=2,
            ),
            LLMProvider(
                name="Mistral",
                model="mistral-large-latest",
                api_key=settings.MISTRAL_API_KEY,
                priority=3,
            ),
        ]

    @property
    def providers(self) -> List[LLMProvider]:
        return list(self._providers)

    def provider_status(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "name": provider.name,
                    "model": provider.model,
                    "configured": provider.configured,
                    "priority": provider.priority,
                    "usage_count": self._usage.get(provider.name, 0),
                }
                for provider in self._providers
            ]

    def usage(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._usage)

    def fallback_history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(item) for item in self._fallback_history]

    def generate(self, prompt: str, **kwargs: Any) -> LLMResponse:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string")

        last_error: Optional[Exception] = None
        for index, provider in enumerate(self._providers):
            if not provider.configured:
                self._record_fallback(
                    from_provider=provider.name,
                    to_provider=self._next_provider_name(index),
                    reason="not_configured",
                )
                continue
            try:
                started = time.perf_counter()
                response = provider.generate(prompt, **kwargs)
                latency_ms = (time.perf_counter() - started) * 1000
                response.latency_ms = latency_ms
                with self._lock:
                    self._usage[provider.name] = self._usage.get(provider.name, 0) + 1
                return response
            except Exception as exc:  # noqa: BLE001 - provider failures must not crash callers
                last_error = exc
                self._record_fallback(
                    from_provider=provider.name,
                    to_provider=self._next_provider_name(index),
                    reason=str(exc),
                )

        raise LLMProviderError(
            "All LLM providers failed: "
            + (str(last_error) if last_error else "no configured provider")
        )

    def _next_provider_name(self, index: int) -> Optional[str]:
        for provider in self._providers[index + 1 :]:
            return provider.name
        return None

    def _record_fallback(
        self,
        from_provider: str,
        to_provider: Optional[str],
        reason: str,
    ) -> None:
        with self._lock:
            self._fallback_history.append(
                {
                    "from_provider": from_provider,
                    "to_provider": to_provider,
                    "reason": reason,
                    "timestamp": time.time(),
                }
            )


# Process-wide gateway instance for backend services.
llm_gateway = LLMGateway()
