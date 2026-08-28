from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RuleScope(StrEnum):
    GLOBAL = "global"
    SYSTEM = "system"
    USER = "user"


class RuleCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    exists: bool | None = None
    equals: Any = None
    requirementsComplete: bool | None = None

    @field_validator("path")
    @classmethod
    def path_is_pointer(cls, value: str) -> str:
        if value != "" and not value.startswith("/"):
            raise ValueError("rule condition path must be a JSON Pointer")
        return value


class ConventionRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    scope: RuleScope = RuleScope.GLOBAL
    system: str | None = None
    path: str
    value: Any
    when: RuleCondition | list[RuleCondition] | None = None
    priority: int = 0


class RulesDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    systemSelectorPath: str = "/metadata/sourceSystemGcpId"
    rules: list[ConventionRule] = Field(default_factory=list)
