from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EvidenceKind(StrEnum):
    USER_MESSAGE = "user_message"
    MCP_ENRICHMENT = "mcp_enrichment"
    MCP_DEFAULT = "mcp_default"
    MCP_DERIVED = "mcp_derived"
    MCP_RULE = "mcp_rule"
    EXTERNAL_SCHEMA = "external_schema"
    EXTERNAL_REPOSITORY = "external_repository"
    EXISTING_CONTRACT = "existing_contract"
    DERIVATION = "derivation"


class ValueOrigin(StrEnum):
    USER_EXPLICIT = "user_explicit"
    USER_PREFERENCE = "user_preference"
    EXISTING_CONTRACT = "existing_contract"
    EXTERNAL_POLICY = "external_policy"
    EXTERNAL_SCHEMA = "external_schema"
    EXTERNAL_REPOSITORY = "external_repository"
    MCP_ENRICHMENT = "mcp_enrichment"
    MCP_DERIVED = "mcp_derived"
    MCP_DEFAULT = "mcp_default"


DEFAULT_ORIGIN_PRIORITY: dict[ValueOrigin, int] = {
    ValueOrigin.USER_EXPLICIT: 100,
    ValueOrigin.USER_PREFERENCE: 90,
    ValueOrigin.EXISTING_CONTRACT: 80,
    ValueOrigin.EXTERNAL_POLICY: 75,
    ValueOrigin.EXTERNAL_SCHEMA: 70,
    ValueOrigin.EXTERNAL_REPOSITORY: 70,
    ValueOrigin.MCP_ENRICHMENT: 60,
    ValueOrigin.MCP_DERIVED: 40,
    ValueOrigin.MCP_DEFAULT: 10,
}


class CandidateScope(StrEnum):
    USER = "user"
    SYSTEM = "system"
    SOURCE_TYPE = "source_type"
    GENERIC = "generic"
    DEFAULT = "default"
    EXTERNAL = "external"


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
    origin: ValueOrigin = ValueOrigin.USER_EXPLICIT
    scope: str = "session"
    evidence_ids: list[UUID] = Field(default_factory=list)
    confidence: float = 1.0
    status: Literal["unbound", "bound", "superseded", "rejected"] = "unbound"
    created_revision: int = 0

    @model_validator(mode="after")
    def require_user_evidence(self) -> "Signal":
        if self.origin == ValueOrigin.USER_EXPLICIT and not self.evidence_ids:
            raise ValueError("USER_EXPLICIT signal requires evidence")
        return self


class Preference(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    concept: str
    value: Any
    origin: ValueOrigin = ValueOrigin.USER_PREFERENCE
    scope: str = "global"
    evidence_ids: list[UUID] = Field(default_factory=list)
    active: bool = True
    created_revision: int = 0

    @model_validator(mode="after")
    def require_user_evidence(self) -> "Preference":
        if self.origin == ValueOrigin.USER_PREFERENCE and not self.evidence_ids:
            raise ValueError("USER_PREFERENCE requires evidence")
        return self


class ValueCandidate(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    path: str
    value: Any
    origin: ValueOrigin
    evidence_ids: list[UUID] = Field(default_factory=list)
    priority: int | None = None
    confidence: float | None = None
    scope: CandidateScope | None = None
    rule_id: str | None = None
    source_signal_id: UUID | None = None
    source_preference_id: UUID | None = None
    created_revision: int = 0
    sequence: int = 0
    status: Literal["candidate", "selected", "rejected", "superseded"] = "candidate"
    reason: str | None = None

    @model_validator(mode="after")
    def require_user_evidence(self) -> "ValueCandidate":
        if self.origin in {ValueOrigin.USER_EXPLICIT, ValueOrigin.USER_PREFERENCE} and not self.evidence_ids:
            raise ValueError(f"{self.origin.value} candidate requires evidence")
        return self

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

    def canonical_hash(self) -> str:
        payload = json.dumps(self.values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AllowedPath(BaseModel):
    path: str
    value_type: str | None = None
    description: str | None = None
    concepts: list[str] = Field(default_factory=list)


class Requirement(BaseModel):
    path: str
    required: bool = True
    prompt_hint: str | None = None


class CapabilityStatus(StrEnum):
    SUCCESS = "success"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


class CapabilityRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    capability: str
    args: dict[str, Any] = Field(default_factory=dict)
    required: bool = True


class CapabilityResult(BaseModel):
    request_id: str
    capability: str
    status: CapabilityStatus
    result: Any = None
    error: str | None = None


class ValidationFindingStatus(StrEnum):
    VALID = "valid"
    INVALID = "invalid"
    DEFERRED = "deferred"


class DependencyType(StrEnum):
    FIELD = "field"
    CAPABILITY = "capability"
    WORKFLOW = "workflow"


class ValidationDependency(BaseModel):
    type: DependencyType
    paths: list[str] = Field(default_factory=list)
    capability: str | None = None
    stage: str | None = None


class ValidationFinding(BaseModel):
    rule_id: str
    status: ValidationFindingStatus
    message: str | None = None
    dependency: ValidationDependency | None = None


class ExternalCandidate(BaseModel):
    path: str
    value: Any
    origin: ValueOrigin
    reason: str | None = None
    evidence: Evidence | None = None
    priority: int | None = None
    scope: CandidateScope | None = None
    rule_id: str | None = None


class EvaluationStatus(StrEnum):
    INCOMPLETE = "incomplete"
    COMPLETE = "complete"
    INVALID = "invalid"


class FinalValidationStatus(StrEnum):
    VALID = "valid"
    INVALID = "invalid"
    DEFERRED_EXTERNAL = "deferred_external"


class RenderMode(StrEnum):
    DRAFT = "draft"
    FINAL = "final"


class CurrentSchemaView(BaseModel):
    schema_revision: str
    stage_id: str | None = None
    allowed_paths: list[AllowedPath] = Field(default_factory=list)

    @property
    def allowed_path_set(self) -> set[str]:
        return {item.path for item in self.allowed_paths}

    @staticmethod
    def _schema_pattern(instance_path: str) -> str:
        import re

        return re.sub(r"\[\d+\]", "[*]", instance_path)

    def is_path_allowed(self, path: str) -> bool:
        if path in self.allowed_path_set:
            return True
        return self._schema_pattern(path) in self.allowed_path_set


class ContractInput(BaseModel):
    draft: dict[str, Any] = Field(default_factory=dict)
    capability_results: list[CapabilityResult] = Field(default_factory=list)
    expected_schema_revision: str | None = None


class ContractEvaluationResult(BaseModel):
    status: EvaluationStatus
    schema_view: CurrentSchemaView
    requirements: list[Requirement] = Field(default_factory=list)
    candidates: list[ExternalCandidate] = Field(default_factory=list)
    validation_findings: list[ValidationFinding] = Field(default_factory=list)
    capability_requests: list[CapabilityRequest] = Field(default_factory=list)


class FinalValidationResult(BaseModel):
    status: FinalValidationStatus
    schema_revision: str
    validation_findings: list[ValidationFinding] = Field(default_factory=list)
    capability_requests: list[CapabilityRequest] = Field(default_factory=list)


class FinalValidationReceipt(BaseModel):
    status: FinalValidationStatus
    draft_hash: str
    schema_revision: str


class RenderRequest(BaseModel):
    draft: dict[str, Any]
    expected_schema_revision: str
    mode: RenderMode


class RenderedContract(BaseModel):
    content: str
    mode: RenderMode
    schema_revision: str


class WorkflowOutcomeStatus(StrEnum):
    WAITING_FOR_USER = "waiting_for_user"
    BLOCKED_EXTERNAL = "blocked_external"
    COMPLETE = "complete"
    INVALID = "invalid"
    FAILED = "failed"


class WorkflowOutcome(BaseModel):
    status: WorkflowOutcomeStatus
    missing_paths: list[str] = Field(default_factory=list)
    draft_changed: bool = False
    draft_hash: str | None = None
    schema_revision: str | None = None
    reason: str | None = None
    final_validation: FinalValidationReceipt | None = None


class WorkflowState(BaseModel):
    current_stage: str | None = None
    current_schema_view: CurrentSchemaView | None = None
    pending_requirements: list[Requirement] = Field(default_factory=list)
    last_evaluation_status: EvaluationStatus | None = None
    capability_results: list[CapabilityResult] = Field(default_factory=list)


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
    candidate_sequence: int = 0
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
