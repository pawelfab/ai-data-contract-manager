from __future__ import annotations

import inspect
import json
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from .models import ChatMessage, Requirement, UserFact


class CandidateValue(BaseModel):
    path: str
    value: Any
    confidence: float = Field(ge=0, le=1)
    evidence: str | None = None


class ExtractionResult(BaseModel):
    values: list[CandidateValue] = Field(default_factory=list)


class SemanticResolver(ABC):
    @abstractmethod
    async def extract_from_history(
        self,
        session_id: str,
        messages: list[ChatMessage],
        pending: list[Requirement],
        overridable: list[Requirement],
        user_facts: list[UserFact],
    ) -> ExtractionResult: ...

    async def close(self) -> None:
        """Release provider resources owned by this resolver, if any."""


class NoopSemanticResolver(SemanticResolver):
    async def extract_from_history(
        self,
        session_id: str,
        messages: list[ChatMessage],
        pending: list[Requirement],
        overridable: list[Requirement],
        user_facts: list[UserFact],
    ) -> ExtractionResult:
        return ExtractionResult()


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
                "Never invent a value. Return only paths present in ALLOWED PATHS. "
                "Use conversation history to reuse information stated earlier when Contract Forge reveals a requirement later. "
                "Correct obvious spelling/casing mistakes only when the intended value is unambiguous. "
                "For pasted columns, normalize them to the schema requested by the requirement. "
                "For every value include a short, exact quote from one user message as evidence. "
                "If evidence is insufficient or ambiguous, omit the value."
            ),
        )

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
        pending: list[Requirement],
        overridable: list[Requirement],
        user_facts: list[UserFact],
    ) -> ExtractionResult:
        del session_id  # Session state is supplied explicitly; the model owns no workflow memory.
        requirements = [*pending, *overridable]
        user_messages = [message for message in messages if message.role == "user"][-20:]
        if not requirements or not user_messages:
            return ExtractionResult()

        allowed_paths = [requirement.path for requirement in requirements]
        pending_payload = [requirement.model_dump(mode="json") for requirement in pending]
        overridable_payload = [
            requirement.model_dump(mode="json") for requirement in overridable
        ]
        facts_payload = [fact.model_dump(mode="json") for fact in user_facts]
        transcript = "\n".join(
            f"[user message_sequence={message.message_sequence}] {message.content}"
            for message in user_messages
        )
        prompt = (
            "ALLOWED PATHS:\n"
            f"{json.dumps(allowed_paths, ensure_ascii=False)}\n\n"
            "PENDING REQUIREMENTS:\n"
            f"{json.dumps(pending_payload, ensure_ascii=False, default=str)}\n\n"
            "OVERRIDABLE VALUES:\n"
            f"{json.dumps(overridable_payload, ensure_ascii=False, default=str)}\n\n"
            "EXISTING USER FACTS:\n"
            f"{json.dumps(facts_payload, ensure_ascii=False, default=str)}\n\n"
            "RECENT USER MESSAGES:\n"
            f"{transcript}\n\n"
            "Return only values directly supported by an exact evidence quote from one user message."
        )
        result = await self.agent.run(prompt)
        return result.output
