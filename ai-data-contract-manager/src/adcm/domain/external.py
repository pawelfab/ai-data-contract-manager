from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class CheckState(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ExternalChecksStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    performed: list[str] = Field(default_factory=list)
    skipped: list[str] = Field(default_factory=list)
    failed: list[str] = Field(default_factory=list)
    degraded: bool = False
