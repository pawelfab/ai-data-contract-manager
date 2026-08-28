from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

PROTOCOL_VERSION = "1.0"


class WritableTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    value_type: str | None = None
    allowed_values: list[Any] | None = None
    title: str | None = None
    description: str | None = None
    activatable: bool = False
    operations: list[str] = Field(default_factory=lambda: ["add", "replace", "remove"])


class MissingRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    code: str = "required"
    message: str | None = None
    expected_type: str | None = None
    allowed_values: list[Any] | None = None


class ForeignLocation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    reason: str
    admissible_fields: list[str] = Field(default_factory=list)


class ForgeProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    path: str
    value: Any
    origin: Literal["enrichment", "default"]
    rule_id: str | None = None
    reason: str | None = None
    derived_from: list[str] = Field(default_factory=list)


class Diagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    path: str | None = None
    severity: Literal["error", "warning"] = "error"
    message: str
    actual_value: Any = None


class ContractStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    valid: bool
    complete: bool
    clean: bool


class ForgeAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    protocol_version: str
    definition_version: str
    writable: list[WritableTarget] = Field(default_factory=list)
    missing: list[MissingRequirement] = Field(default_factory=list)
    foreign: list[ForeignLocation] = Field(default_factory=list)
    proposals: list[ForgeProposal] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    status: ContractStatus


class FieldDescriptor(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path_pattern: str
    value_type: str | None = None
    required: bool = False
    allowed_values: list[Any] | None = None
    title: str | None = None
    description: str | None = None


class ForgeDescription(BaseModel):
    model_config = ConfigDict(extra="forbid")
    protocol_version: str
    definition_version: str
    fields: list[FieldDescriptor] = Field(default_factory=list)
