from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from app.core.logging import logger


class BaseAgent(ABC):
    """Base class for all due diligence agents."""

    def __init__(self, name: str):
        self.name = name
        self.logger = logger

    @abstractmethod
    async def run(self, startup_id: int, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the agent's due diligence task."""
        pass

    async def execute(self, startup_id: int, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Wrapper around run with logging and error handling."""
        self.logger.info(f"Agent {self.name} starting for startup {startup_id}")
        try:
            result = await self.run(startup_id, context)
            self.logger.info(f"Agent {self.name} completed for startup {startup_id}")
            return {
                "agent_name": self.name,
                "startup_id": startup_id,
                "result": result,
                "status": "success",
            }
        except Exception as e:
            self.logger.error(f"Agent {self.name} failed for startup {startup_id}: {e}")
            return {
                "agent_name": self.name,
                "startup_id": startup_id,
                "result": {},
                "status": "error",
                "error": str(e),
            }
