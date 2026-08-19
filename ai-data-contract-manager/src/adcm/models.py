from __future__ import annotations

from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field


class Origin(str, Enum):
    """Value provenance accepted by the Contract Forge MCP wire contract."""

    USER = "user"
    SYSTEM_ENRICHMENT = "system_enrichment"
    GENERIC_ENRICHMENT = "generic_enrichment"
    SCHEMA_DEFAULT = "schema_default"
    STRUCTURAL = "structural"


class ExtractionMethod(str, Enum):
    DETERMINISTIC = "deterministic"
    LLM = "llm"


class Requirement(BaseModel):
    path: str
    question: str
    reason: Literal["source_system", "required", "one_of", "invalid"] = "required"
    input_mode: Literal["explicit", "semantic"] = "semantic"
    value_schema: dict[str, Any] = Field(default_factory=dict)
    unsupported_schema_keywords: list[str] = Field(default_factory=list)
    allowed_values: list[Any] | None = None
    allow_custom_value: bool = False
    current_value: Any | None = None
    current_origin: Origin | None = None


class ValidationIssue(BaseModel):
    path: str
    message: str
    validator: str | None = None


class AppliedValue(BaseModel):
    path: str
    value: Any
    origin: Origin
    rule_id: str | None = None


class RuleIssue(BaseModel):
    rule_id: str
    path: str | None = None
    reason: str


class ForgeState(BaseModel):
    """Client-side DTO validated from Contract Forge MCP responses."""

    session_id: str
    source_system: str | None = None
    contract: dict[str, Any] = Field(default_factory=dict)
    origins: dict[str, str] = Field(default_factory=dict)
    status: Literal["needs_input", "complete", "invalid"] = "needs_input"
    pending: list[Requirement] = Field(default_factory=list)
    overridable: list[Requirement] = Field(default_factory=list)
    validation_errors: list[ValidationIssue] = Field(default_factory=list)
    candidate_issues: list[ValidationIssue] = Field(default_factory=list)
    applied: list[AppliedValue] = Field(default_factory=list)
    rule_issues: list[RuleIssue] = Field(default_factory=list)


class AssistantTurn(BaseModel):
    session_id: str
    message: str
    status: Literal["needs_input", "complete", "invalid"]
    pending_path: str | None = None
    pending_requirement: Requirement | None = None
    contract: dict[str, Any] = Field(default_factory=dict)
    validation_errors: list[dict[str, Any]] = Field(default_factory=list)
    candidate_issues: list[dict[str, Any]] = Field(default_factory=list)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    message_sequence: int | None = Field(default=None, ge=1)


class UserFact(BaseModel):
    path: str
    value: Any
    message_sequence: int = Field(ge=1)
    extraction_method: ExtractionMethod
    confidence: float = Field(default=1.0, ge=0, le=1)
    evidence: str | None = None


class PartialFact(BaseModel):
    path: str
    value: Any
    missing: list[str] = Field(default_factory=list)
    invalid: list[str] = Field(default_factory=list)
    message_sequence: int = Field(ge=1)
    evidence: str | None = None


class ConversationMemory(BaseModel):
    session_id: str
    forge_session_id: str
    messages: list[ChatMessage] = Field(default_factory=list)
    facts: dict[str, UserFact] = Field(default_factory=dict)
    partial_facts: dict[str, PartialFact] = Field(default_factory=dict)
    next_message_sequence: int = Field(default=1, ge=1)

    def add_user_message(self, content: str) -> ChatMessage:
        message = ChatMessage(
            role="user",
            content=content,
            message_sequence=self.next_message_sequence,
        )
        self.next_message_sequence += 1
        self.messages.append(message)
        return message

    def add_assistant_message(self, content: str) -> ChatMessage:
        message = ChatMessage(role="assistant", content=content)
        self.messages.append(message)
        return message

    def remember_fact(self, fact: UserFact) -> bool:
        current = self.facts.get(fact.path)
        if current is not None and fact.message_sequence < current.message_sequence:
            return False
        self.facts[fact.path] = fact.model_copy(deep=True)
        return True

    def get_fact(self, path: str) -> UserFact | None:
        return self.facts.get(path)

    def forget_fact(self, path: str) -> None:
        self.facts.pop(path, None)

    def remember_partial(self, partial: PartialFact) -> bool:
        current = self.partial_facts.get(partial.path)
        if current is not None and partial.message_sequence < current.message_sequence:
            return False
        self.partial_facts[partial.path] = partial.model_copy(deep=True)
        return True

    def get_partial(self, path: str) -> PartialFact | None:
        return self.partial_facts.get(path)

    def clear_partial(self, path: str) -> None:
        self.partial_facts.pop(path, None)
