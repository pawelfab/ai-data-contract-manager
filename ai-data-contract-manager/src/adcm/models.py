from __future__ import annotations

from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field


class Origin(str, Enum):
    """Value provenance accepted by the Contract Forge MCP wire contract."""

    USER = "user"
    LLM = "llm"
    SYSTEM_ENRICHMENT = "system_enrichment"
    GENERIC_ENRICHMENT = "generic_enrichment"
    SCHEMA_DEFAULT = "schema_default"
    STRUCTURAL = "structural"


class Requirement(BaseModel):
    path: str
    question: str
    reason: Literal["source_system", "required", "one_of", "invalid"] = "required"
    input_mode: Literal["explicit", "semantic"] = "semantic"
    value_schema: dict[str, Any] = Field(default_factory=dict)
    allowed_values: list[Any] | None = None


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
    validation_errors: list[ValidationIssue] = Field(default_factory=list)
    applied: list[AppliedValue] = Field(default_factory=list)
    rule_issues: list[RuleIssue] = Field(default_factory=list)


class AssistantTurn(BaseModel):
    session_id: str
    message: str
    status: Literal["needs_input", "complete", "invalid"]
    pending_path: str | None = None
    contract: dict[str, Any] = Field(default_factory=dict)
    validation_errors: list[dict[str, Any]] = Field(default_factory=list)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ConversationMemory(BaseModel):
    session_id: str
    forge_session_id: str
    messages: list[ChatMessage] = Field(default_factory=list)
