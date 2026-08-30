from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .external import ExternalChecksStatus
from .forge import ForgeAnalysis
from .mutations import MutationCandidate, MutationEvent


class IntentKind(StrEnum):
    MUTATION = "mutation"
    KNOWLEDGE = "knowledge"
    MIXED = "mixed"
    UNRESOLVED = "unresolved"


class IntentResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")
    intent_kind: IntentKind
    candidates: list[MutationCandidate] = Field(default_factory=list)
    knowledge_query: str | None = None
    unresolved: list[dict[str, Any]] = Field(default_factory=list)


class EffectiveIntentResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")
    intent_kind: IntentKind
    candidates: list[MutationCandidate] = Field(default_factory=list)
    knowledge_query: str | None = None
    unresolved: list[dict[str, Any]] = Field(default_factory=list)


class StabilizationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rounds: int
    converged: bool
    proposal_decisions: list[dict] = Field(default_factory=list)
    foreign_removed: list[str] = Field(default_factory=list)


class TurnOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    turn_no: int
    message: str
    document: dict
    forge: ForgeAnalysis
    external_checks: ExternalChecksStatus
    new_events: list[MutationEvent]
    stabilization: StabilizationReport
    intent_kind: IntentKind
    # Przeniesione z IntentResolution: czego tura nie zrozumiała. Bez tego wynik
    # resolvera kończy się w Session Audit i nigdy nie wraca do użytkownika.
    unresolved: list[dict[str, Any]] = Field(default_factory=list)
