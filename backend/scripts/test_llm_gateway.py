import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.llm.gateway import LLMGateway
from app.schemas.llm_outputs import ControllerOutput


async def main():
    gateway = LLMGateway(providers=[], mock_mode=True)
    result = await gateway.generate(
        agent_name="Controller Agent",
        prompt="Summarize a startup called Acme.",
        response_schema=ControllerOutput,
    )
    print("Provider:", result.provider)
    print("Model:", result.model)
    print("Parsed:", result.parsed)


if __name__ == "__main__":
    asyncio.run(main())
