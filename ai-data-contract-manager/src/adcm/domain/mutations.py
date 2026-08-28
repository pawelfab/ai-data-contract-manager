from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .provenance import ValueSource


class CandidateAction(StrEnum):
    SET = "set"
    REMOVE = "remove"


class MutationOperation(StrEnum):
    ADD = "add"
    REPLACE = "replace"
    REMOVE = "remove"


class MutationCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: uuid4().hex)
    action: CandidateAction
    path: str
    value: Any = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence: str | None = None


class MutationCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: uuid4().hex)
    operation: MutationOperation
    path: str
    value: Any = None
    source: ValueSource
    producer_id: str | None = None
    derived_from: list[str] = Field(default_factory=list)
    reason: str | None = None


class MutationEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mutation_id: str
    revision_before: int
    revision_after: int
    operation: MutationOperation
    path: str
    old_exists: bool
    old_value: Any = None
    new_exists: bool
    new_value: Any = None
    source: ValueSource
    producer_id: str | None = None
    reason: str | None = None
