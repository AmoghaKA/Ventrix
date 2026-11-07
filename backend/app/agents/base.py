from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pydantic import BaseModel

from app.core.logging import logger


class BaseAgent(ABC):
    """Base class for all due diligence agents.

    Agents may return a plain dictionary for backwards compatibility or a
    Pydantic model for structured output. Structured models are returned
    unchanged so callers receive the schema defined by the agent.
    """

    agent_key: Optional[str] = None
    AGENT_NAME: str = "Base Agent"

    def __init__(self, name: str):
        self.name = name
        self.logger = logger
        if self.agent_key is None:
            self.agent_key = name.strip().lower().replace(" ", "_")

    @abstractmethod
    async def run(
        self,
        startup_id: int,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute the agent's due diligence task."""
        pass

    async def execute(
        self,
        startup_id: int,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Wrapper around run with logging and structured error handling."""
        self.logger.info(f"Agent {self.name} starting for startup {startup_id}")
        try:
            result = await self.run(startup_id, context)
            if isinstance(result, BaseModel):
                execution_status = getattr(result, "execution_status", None)
                status_value = getattr(execution_status, "value", execution_status)
                if status_value == "FAILED":
                    self.logger.error(
                        f"Agent {self.name} returned a failed output for "
                        f"startup {startup_id}"
                    )
                else:
                    self.logger.info(
                        f"Agent {self.name} completed for startup {startup_id}"
                    )
                return result
            self.logger.info(f"Agent {self.name} completed for startup {startup_id}")
            return {
                "agent_name": self.name,
                "startup_id": startup_id,
                "result": result,
                "status": "success",
            }
        except Exception as e:
            self.logger.error(f"Agent {self.name} failed for startup {startup_id}: {e}")
            structured_error = self.structured_error_output(startup_id, context, e)
            if structured_error is not None:
                return structured_error
            return {
                "agent_name": self.name,
                "startup_id": startup_id,
                "result": {},
                "status": "error",
                "error": str(e),
            }

    def structured_error_output(
        self,
        startup_id: int,
        context: Optional[Dict[str, Any]],
        error: Exception,
    ) -> Optional[BaseModel]:
        """Return a structured error model when the agent supports one."""
        return None
