from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from contract_forge.models import Requirement
from .models import ChatMessage


class CandidateValue(BaseModel):
    path: str
    value: Any
    confidence: float = Field(ge=0, le=1)
    evidence: str


class ExtractionResult(BaseModel):
    values: list[CandidateValue] = Field(default_factory=list)


class SemanticResolver(ABC):
    @abstractmethod
    async def extract_from_history(
        self,
        session_id: str,
        messages: list[ChatMessage],
        requirements: list[Requirement],
        contract: dict[str, Any],
    ) -> dict[str, Any]: ...


class NoopSemanticResolver(SemanticResolver):
    async def extract_from_history(self, session_id, messages, requirements, contract) -> dict[str, Any]:
        return {}


class PydanticAISemanticResolver(SemanticResolver):
    """Semantic extraction only; it never owns contract progression or tool selection."""

    def __init__(self, model: Any = None):
        try:
            from pydantic_ai import Agent
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError('Install Pydantic AI extras: pip install -e ".[mcp]"') from exc

        if model is None:
            vertex_model = os.getenv("ADCM_VERTEX_MODEL")
            if vertex_model:
                from pydantic_ai.models.google import GoogleModel
                model = GoogleModel(vertex_model, provider="google-cloud")
            else:
                model = os.getenv("ADCM_MODEL", "openai:gpt-5.2")

        self.agent = Agent(
            model,
            output_type=ExtractionResult,
            instructions=(
                "You extract facts already stated by the user for a contract-building workflow. "
                "Never invent a value. Return only paths present in CURRENT REQUIREMENTS. "
                "Use conversation history to reuse information stated earlier when Contract Forge reveals a requirement later. "
                "Correct obvious spelling/casing mistakes only when the intended value is unambiguous. "
                "For pasted columns, normalize them to the schema requested by the requirement. "
                "If evidence is insufficient, omit the value."
            ),
        )
        self.histories: dict[str, list[Any]] = {}

    async def extract_from_history(
        self,
        session_id: str,
        messages: list[ChatMessage],
        requirements: list[Requirement],
        contract: dict[str, Any],
    ) -> dict[str, Any]:
        if not requirements or not messages:
            return {}

        req_payload = [r.model_dump(mode="json") for r in requirements]
        transcript = "\n".join(f"{m.role}: {m.content}" for m in messages[-20:])
        prompt = (
            "CURRENT REQUIREMENTS:\n"
            f"{req_payload}\n\n"
            "CURRENT CONTRACT (read-only context):\n"
            f"{contract}\n\n"
            "CONVERSATION:\n"
            f"{transcript}\n\n"
            "Return only values directly supported by the conversation."
        )
        history = self.histories.get(session_id)
        result = await self.agent.run(prompt, message_history=history)
        try:
            self.histories[session_id] = result.all_messages()
        except AttributeError:  # pragma: no cover - compatibility fallback
            self.histories[session_id] = result.new_messages()

        allowed = {r.path for r in requirements}
        return {
            item.path: item.value
            for item in result.output.values
            if item.path in allowed and item.confidence >= 0.80
        }
