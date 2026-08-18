from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EvidenceKind(StrEnum):
    USER_MESSAGE = "user_message"
    MCP_ENRICHMENT = "mcp_enrichment"
    MCP_DEFAULT = "mcp_default"
    MCP_DERIVED = "mcp_derived"
    MCP_RULE = "mcp_rule"
    EXTERNAL_SCHEMA = "external_schema"
    EXISTING_CONTRACT = "existing_contract"
    GITHUB_FILE = "github_file"
    DERIVATION = "derivation"


class ValueOrigin(StrEnum):
    USER_EXPLICIT = "user_explicit"
    USER_PREFERENCE = "user_preference"
    EXISTING_CONTRACT = "existing_contract"
    EXTERNAL_SCHEMA = "external_schema"
    MCP_ENRICHMENT = "mcp_enrichment"
    MCP_DERIVED = "mcp_derived"
    MCP_DEFAULT = "mcp_default"


DEFAULT_ORIGIN_PRIORITY: dict[ValueOrigin, int] = {
    ValueOrigin.USER_EXPLICIT: 100,
    ValueOrigin.USER_PREFERENCE: 90,
    ValueOrigin.EXISTING_CONTRACT: 80,
    ValueOrigin.EXTERNAL_SCHEMA: 70,
    ValueOrigin.MCP_ENRICHMENT: 60,
    ValueOrigin.MCP_DERIVED: 40,
    ValueOrigin.MCP_DEFAULT: 10,
}


class Evidence(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    kind: EvidenceKind
    source_id: str | None = None
    content: Any
    message_id: UUID | None = None
    tool_call_id: str | None = None
    timestamp: datetime = Field(default_factory=utcnow)


class Signal(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    concept: str
    value: Any
    scope: str = "session"
    evidence_ids: list[UUID] = Field(default_factory=list)
    confidence: float = 1.0
    status: Literal["unbound", "bound", "superseded", "rejected"] = "unbound"


class Preference(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    concept: str
    value: Any
    scope: str = "global"
    evidence_ids: list[UUID] = Field(default_factory=list)
    active: bool = True


class ValueCandidate(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    path: str
    value: Any
    origin: ValueOrigin
    evidence_ids: list[UUID] = Field(default_factory=list)
    priority: int | None = None
    confidence: float | None = None
    status: Literal["candidate", "selected", "rejected", "superseded"] = "candidate"
    reason: str | None = None

    def effective_priority(self) -> int:
        return self.priority if self.priority is not None else DEFAULT_ORIGIN_PRIORITY[self.origin]


class ResolvedValue(BaseModel):
    path: str
    value: Any
    selected_candidate_id: UUID
    origin: ValueOrigin
    evidence_ids: list[UUID] = Field(default_factory=list)


class ContractDraft(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)
    revision: int = 0


class AllowedPath(BaseModel):
    path: str
    value_type: str | None = None
    description: str | None = None
    concepts: list[str] = Field(default_factory=list)


class Requirement(BaseModel):
    path: str
    required: bool = True
    prompt_hint: str | None = None


class CapabilityRequest(BaseModel):
    capability: str
    args: dict[str, Any] = Field(default_factory=dict)
    required: bool = True


class ExternalCandidate(BaseModel):
    path: str
    value: Any
    origin: ValueOrigin
    reason: str | None = None
    evidence: Evidence | None = None
    priority: int | None = None


class RequirementBundle(BaseModel):
    stage_id: str
    allowed_paths: list[AllowedPath] = Field(default_factory=list)
    requirements: list[Requirement] = Field(default_factory=list)
    candidates: list[ExternalCandidate] = Field(default_factory=list)
    capability_requests: list[CapabilityRequest] = Field(default_factory=list)
    complete: bool = False

    @property
    def allowed_path_set(self) -> set[str]:
        return {p.path for p in self.allowed_paths}


class WorkflowState(BaseModel):
    current_stage: str | None = None
    completed_stages: list[str] = Field(default_factory=list)
    allowed_paths: set[str] = Field(default_factory=set)
    pending_requirements: list[Requirement] = Field(default_factory=list)
    complete: bool = False


class ValueChange(BaseModel):
    path: str | None = None
    concept: str | None = None
    old: Any = None
    new: Any = None
    reason: str


class Revision(BaseModel):
    revision: int
    changes: list[ValueChange]
    trigger_message_id: UUID | None = None
    timestamp: datetime = Field(default_factory=utcnow)


class AuditEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    event_type: str
    payload: dict[str, Any]
    session_id: UUID
    revision: int
    timestamp: datetime = Field(default_factory=utcnow)


class ChatMessage(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = Field(default_factory=utcnow)


class ExtractedSignal(BaseModel):
    concept: str
    value: Any
    scope: str = "session"
    confidence: float = 1.0


class ExtractedPreference(BaseModel):
    concept: str
    value: Any
    scope: str = "global"
    confidence: float = 1.0


class CorrectionIntent(BaseModel):
    concept: str
    new_value: Any
    previous_value: Any | None = None
    intent: Literal["replace", "uncertain"] = "replace"


class PossibleTypo(BaseModel):
    text: str
    candidate: str
    confidence: float
    concept: str | None = None


class TurnInterpretation(BaseModel):
    intent: str = "provide_information"
    extracted_signals: list[ExtractedSignal] = Field(default_factory=list)
    preferences: list[ExtractedPreference] = Field(default_factory=list)
    corrections: list[CorrectionIntent] = Field(default_factory=list)
    possible_typos: list[PossibleTypo] = Field(default_factory=list)


class ConversationState(BaseModel):
    session_id: UUID = Field(default_factory=uuid4)
    revision: int = 0
    messages: list[ChatMessage] = Field(default_factory=list)
    signals: list[Signal] = Field(default_factory=list)
    preferences: list[Preference] = Field(default_factory=list)
    value_candidates: list[ValueCandidate] = Field(default_factory=list)
    resolved_values: dict[str, ResolvedValue] = Field(default_factory=dict)
    contract_draft: ContractDraft = Field(default_factory=ContractDraft)
    workflow: WorkflowState = Field(default_factory=WorkflowState)
    evidence: list[Evidence] = Field(default_factory=list)
    revisions: list[Revision] = Field(default_factory=list)
    audit_events: list[AuditEvent] = Field(default_factory=list)


class SignalView(BaseModel):
    id: UUID
    concept: str
    value: Any
    status: str


class PreferenceView(BaseModel):
    id: UUID
    concept: str
    value: Any
    scope: str


class AgentContext(BaseModel):
    current_stage: str | None
    active_signals: list[SignalView]
    active_preferences: list[PreferenceView]
    known_values: dict[str, Any]
    allowed_paths: list[str]
    pending_requirements: list[Requirement]
    recent_messages: list[ChatMessage]
