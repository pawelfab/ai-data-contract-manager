from pydantic import BaseModel, ConfigDict, Field

from contract_forge.domain.evaluation.models import Requirement


class DiscoveryStep(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str
    when_missing: list[str] = Field(default_factory=list, alias="whenMissing")
    when_any_missing: list[str] = Field(default_factory=list, alias="whenAnyMissing")
    when_present: list[str] = Field(default_factory=list, alias="whenPresent")
    expose: list[str] = Field(default_factory=list)
    expose_matching_schema_requirements: bool = Field(False, alias="exposeMatchingSchemaRequirements")


class RequirementPresentation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    display_name: str | None = Field(None, alias="displayName")
    help_text: str | None = Field(None, alias="helpText")


class DiscoveryPolicy(BaseModel):
    version: str | None = None
    steps: list[DiscoveryStep] = Field(default_factory=list)
    presentation: dict[str, RequirementPresentation] = Field(default_factory=dict)


class DiscoveryPolicyIssue(BaseModel):
    step_id: str | None = None
    path: str | None = None
    message: str


class DiscoveryOutcome(BaseModel):
    requirements: list[Requirement] = Field(default_factory=list)
    issues: list[DiscoveryPolicyIssue] = Field(default_factory=list)
