from abc import ABC, abstractmethod
from typing import Any, Dict


class LLMProviderError(Exception):
    """Raised when an LLM provider cannot complete a request."""


class BaseLLMProvider(ABC):
    name: str = ""
    model: str = ""
    api_key: str = ""
    timeout_seconds: float = 30.0
    priority: int = 0

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    @abstractmethod
    async def generate_text(self, prompt: str, response_schema=None) -> str:
        """Return raw text from the provider."""
        raise NotImplementedError

    def status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "model": self.model,
            "configured": self.configured,
        }
