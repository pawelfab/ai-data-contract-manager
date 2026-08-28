from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .provenance import ValueSource


class ProposalMode(StrEnum):
    SET = "set"
    ENSURE_PRESENT = "ensure_present"


class ProposalAction(StrEnum):
    APPLY = "apply"
    KEEP_CURRENT = "keep_current"
    REMOVE_STALE = "remove_stale"
    CONFLICT = "conflict"


class Proposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    path: str
    value: Any
    source: ValueSource
    producer_id: str
    priority: int = 0
    specificity: int = 0
    reason: str | None = None
    derived_from: list[str] = Field(default_factory=list)
    mode: ProposalMode = ProposalMode.SET


class ProposalDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    action: ProposalAction
    proposal_id: str | None = None
    reason: str
