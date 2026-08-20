from __future__ import annotations

from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field


class Origin(str, Enum):
    USER = "user"
    SYSTEM_ENRICHMENT = "system_enrichment"
    GENERIC_ENRICHMENT = "generic_enrichment"
    SCHEMA_DEFAULT = "schema_default"
    STRUCTURAL = "structural"


ORIGIN_PRIORITY: dict[Origin, int] = {
    Origin.USER: 100,
    Origin.SYSTEM_ENRICHMENT: 70,
    Origin.GENERIC_ENRICHMENT: 60,
    Origin.SCHEMA_DEFAULT: 50,
    Origin.STRUCTURAL: 10,
}

OVERRIDABLE_ORIGINS = frozenset(
    {
        Origin.SYSTEM_ENRICHMENT,
        Origin.GENERIC_ENRICHMENT,
        Origin.SCHEMA_DEFAULT,
    }
)


def can_replace(current: Origin | None, candidate: Origin) -> bool:
    """Return whether a candidate origin may replace the current value origin."""
    if current is None:
        return True
    if current == candidate:
        # A later USER submit represents the client's current intent. Forge does not
        # compare message sequence; enrichment/default writes remain fill-only.
        return candidate == Origin.USER
    return ORIGIN_PRIORITY[candidate] > ORIGIN_PRIORITY[current]


class Requirement(BaseModel):
    """One thing Forge needs from ADCM before the contract can be completed.

    ``status`` says what ADCM has to do; ``reason`` says why the requirement exists.
    They are separate axes on purpose: ``reason`` is descriptive metadata that may grow
    new values, ``status`` is the stable operational field ADCM branches on.
    """

    path: str
    # missing   -> try UserFact, heuristics, LLM, then ask the user
    # invalid   -> a value exists but is wrong; ask for a correction
    # forbidden -> a disallowed section/combination is present; ask for its removal
    status: Literal["missing", "invalid", "forbidden"] = "missing"
    # Deliberately a plain str, not a Literal: new discovery reasons must not break the
    # transport boundary. Current values: source_system, required, one_of, invalid,
    # contract_rule.
    reason: str = "required"
    rule_id: str | None = None
    message: str | None = None
    question: str | None = None
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


class ContractRuleIssue(BaseModel):
    """Outcome of one ``x-contract-rule`` evaluated against the current contract.

    ``skipped_non_executable`` marks a rule whose logic is not expressed structurally
    (no ``assertion``), so it is reported but never blocks completion.
    """

    rule_id: str
    status: Literal["missing", "invalid", "forbidden", "skipped_non_executable"]
    path: str | None = None
    message: str
    severity: str = "error"
    detail: str | None = None


class ForgeState(BaseModel):
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
    contract_rule_issues: list[ContractRuleIssue] = Field(default_factory=list)


class SessionData(BaseModel):
    session_id: str
    source_system: str | None = None
    contract: dict[str, Any] = Field(default_factory=dict)
    origins: dict[str, Origin] = Field(default_factory=dict)
    applied: list[AppliedValue] = Field(default_factory=list)
    candidate_issues: list[ValidationIssue] = Field(default_factory=list)
