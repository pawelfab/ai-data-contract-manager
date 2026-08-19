from __future__ import annotations

from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field


class Origin(str, Enum):
    USER = "user"
    LLM = "llm"
    SYSTEM_ENRICHMENT = "system_enrichment"
    GENERIC_ENRICHMENT = "generic_enrichment"
    SCHEMA_DEFAULT = "schema_default"
    STRUCTURAL = "structural"


ORIGIN_PRIORITY: dict[Origin, int] = {
    Origin.USER: 100,
    Origin.LLM: 90,
    Origin.SYSTEM_ENRICHMENT: 70,
    Origin.GENERIC_ENRICHMENT: 60,
    Origin.SCHEMA_DEFAULT: 50,
    Origin.STRUCTURAL: 10,
}


class Requirement(BaseModel):
    path: str
    question: str
    reason: Literal["source_system", "required", "one_of", "invalid"] = "required"
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
    session_id: str
    source_system: str | None = None
    contract: dict[str, Any] = Field(default_factory=dict)
    origins: dict[str, str] = Field(default_factory=dict)
    status: Literal["needs_input", "complete", "invalid"] = "needs_input"
    pending: list[Requirement] = Field(default_factory=list)
    validation_errors: list[ValidationIssue] = Field(default_factory=list)
    applied: list[AppliedValue] = Field(default_factory=list)
    rule_issues: list[RuleIssue] = Field(default_factory=list)


class SessionData(BaseModel):
    session_id: str
    source_system: str | None = None
    contract: dict[str, Any] = Field(default_factory=dict)
    origins: dict[str, Origin] = Field(default_factory=dict)
    applied: list[AppliedValue] = Field(default_factory=list)
