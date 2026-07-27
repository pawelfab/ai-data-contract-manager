from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FieldGuidance(StrictModel):
    path: str
    kind: str
    required: bool
    description: str
    examples: list[Any] = Field(default_factory=list)
    default: Any | None = None
    enum: list[Any] = Field(default_factory=list)
    const: Any | None = None
    item_required: list[str] = Field(default_factory=list)
    item_properties: dict[str, dict[str, Any]] = Field(default_factory=dict)
    condition: str | None = None
    required_if_path: str | None = None


class RequirementQuestion(StrictModel):
    path: str
    question: str
    description: str
    examples: list[Any] = Field(default_factory=list)


class OptionalDecision(StrictModel):
    path: str
    label: str
    question: str
    description: str
    examples: list[Any] = Field(default_factory=list)


class RequirementsCatalogue(StrictModel):
    schema_fingerprint: str
    fingerprint: str
    source_type: str
    target_layers: list[str]
    source_types: list[str]
    target_order: list[str]
    required_paths: list[str]
    optional_paths: list[str]
    allowed_paths: list[str]
    questions: list[RequirementQuestion]
    optional_decisions: list[OptionalDecision]
    field_catalog: list[FieldGuidance]


class ValidationIssue(StrictModel):
    path: str
    code: str
    message: str
    description: str
    value: Any | None = None


class ValidationResult(StrictModel):
    valid: bool
    contract_fingerprint: str
    schema_fingerprint: str
    issues: list[ValidationIssue] = Field(default_factory=list)
    normalized_contract: dict[str, Any]


class YamlResult(StrictModel):
    yaml: str
    contract_fingerprint: str
    schema_fingerprint: str
