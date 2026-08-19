from __future__ import annotations

import inspect
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

    async def close(self) -> None:
        """Release provider resources owned by this resolver, if any."""


class NoopSemanticResolver(SemanticResolver):
    async def extract_from_history(self, session_id, messages, requirements, contract) -> dict[str, Any]:
        return {}


class PydanticAISemanticResolver(SemanticResolver):
    """Semantic extraction only; it never owns contract progression or tool selection."""

    def __init__(self, model: Any):
        try:
            from pydantic_ai import Agent
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError('Install Pydantic AI extras: pip install -e ".[openai]" or ".[vertex]"') from exc

        self.model = model
        self.agent = Agent(
            model,
            name="contract_fact_extractor",
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

    async def close(self) -> None:
        client = getattr(self.model, "client", None)
        close = getattr(client, "close", None)
        if close is None:
            return
        result = close()
        if inspect.isawaitable(result):
            await result

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
