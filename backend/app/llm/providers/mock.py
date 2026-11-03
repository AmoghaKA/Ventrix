import json
from typing import Any, Optional, get_args, get_origin

from pydantic import BaseModel

from app.llm.providers.base import BaseLLMProvider


def _mock_value(annotation: Any) -> Any:
    origin = get_origin(annotation)
    if origin is list:
        return []
    if origin is dict:
        return {}
    if origin is not None:
        args = [arg for arg in get_args(annotation) if arg is not type(None)]
        if args:
            return _mock_value(args[0])
    if annotation is str:
        return "mock"
    if annotation is int:
        return 0
    if annotation is float:
        return 0.0
    if annotation is bool:
        return False
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return _mock_object(annotation)
    return None


def _mock_object(schema: type[BaseModel]) -> dict:
    from pydantic_core import PydanticUndefined

    result = {}
    for name, field in schema.model_fields.items():
        if field.default is not PydanticUndefined:
            result[name] = field.default
            continue
        if field.default_factory is not None:
            try:
                result[name] = field.default_factory()
                continue
            except Exception:
                pass
        result[name] = _mock_value(field.annotation)
    return result


class MockProvider(BaseLLMProvider):
    name = "Mock LLM"
    model = "mock-model"

    def __init__(self, timeout_seconds: float = 1.0):
        self.api_key = "mock"
        self.timeout_seconds = timeout_seconds

    async def generate_text(self, prompt: str, response_schema: Optional[type[BaseModel]] = None) -> str:
        if response_schema is None:
            return json.dumps({"message": "mock response"})
        return json.dumps(_mock_object(response_schema))
