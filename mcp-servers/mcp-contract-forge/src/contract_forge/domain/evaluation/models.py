from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Requirement(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    path: str
    kind: str = "schema"
    title: str | None = None
    description: str | None = None
    expected_type: str | None = Field(None, alias="expectedType")
    display_name: str | None = Field(None, alias="displayName")
    help_text: str | None = Field(None, alias="helpText")


class SuggestedValue(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    path: str
    value: Any
    source: str
    priority: int = 0
    source_ref: str | None = Field(None, alias="sourceRef")
    rule_id: str | None = Field(None, alias="ruleId")


class ValidationIssue(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    path: str | None = None
    severity: str = "error"
    message: str
    rule_id: str | None = Field(None, alias="ruleId")


class ForgeEvaluation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    api_version: str = Field("1", alias="apiVersion")
    forge_version: str = Field("0.4.1", alias="forgeVersion")
    schema_version: str | None = Field(None, alias="schemaVersion")
    rules_spec_version: str | None = Field(None, alias="rulesSpecVersion")
    requirements: list[Requirement] = Field(default_factory=list)
    suggestions: list[SuggestedValue] = Field(default_factory=list)
    issues: list[ValidationIssue] = Field(default_factory=list)
    valid: bool = False
