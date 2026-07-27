from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FieldGuidance(StrictModel):
    path: str
    kind: str
    required: bool
    description: str
    examples: list[Any] = Field(default_factory=list)
    default: Any | None = None
    enum: list[Any] = Field(default_factory=list)
    const: Any | None = None
    item_required: list[str] = Field(default_factory=list)
    item_properties: dict[str, dict[str, Any]] = Field(default_factory=dict)
    condition: str | None = None
    required_if_path: str | None = None


class RequirementQuestion(StrictModel):
    path: str
    question: str
    description: str
    examples: list[Any] = Field(default_factory=list)


class OptionalDecision(StrictModel):
    path: str
    label: str
    question: str
    description: str
    examples: list[Any] = Field(default_factory=list)


class RequirementsCatalogue(StrictModel):
    schema_fingerprint: str
    fingerprint: str
    source_type: str
    target_layers: list[str]
    source_types: list[str]
    target_order: list[str]
    required_paths: list[str]
    optional_paths: list[str]
    allowed_paths: list[str]
    questions: list[RequirementQuestion]
    optional_decisions: list[OptionalDecision]
    field_catalog: list[FieldGuidance]


class EvidenceItem(StrictModel):
    path: str
    value: Any
    source: Literal["user", "document", "mcp", "validation_repair"]
    confidence: float = Field(ge=0, le=1)
    evidence_text: str
    revision: int


class ValidationIssue(StrictModel):
    path: str
    code: str
    message: str
    description: str
    value: Any | None = None


class ValidationResult(StrictModel):
    valid: bool
    contract_fingerprint: str
    schema_fingerprint: str
    issues: list[ValidationIssue] = Field(default_factory=list)
    normalized_contract: dict[str, Any]


class YamlResult(StrictModel):
    yaml: str
    contract_fingerprint: str
    schema_fingerprint: str


class PatchOperation(StrictModel):
    path: str = Field(
        description="Dokładna ścieżka otrzymana w allowed_paths z MCP."
    )
    value: Any = Field(description="Wartość wynikająca z rozmowy lub evidence.")
    confidence: float = Field(default=1.0, ge=0, le=1)
    evidence_text: str = Field(
        description="Krótki cytat lub parafraza podstawy tej wartości."
    )


class OptionalDecisionUpdate(StrictModel):
    path: str = Field(
        description="Ścieżka sekcji z optional_decisions aktywnego katalogu MCP."
    )
    include: bool = Field(
        description="True, gdy użytkownik chce sekcję uzupełnić; False, gdy ją pomija."
    )


class ValidationSnapshot(StrictModel):
    draft_fingerprint: str
    result: ValidationResult


class ContractState(StrictModel):
    conversation_id: str
    revision: int = 0
    source_type: str | None = None
    target_layers: list[str] = Field(default_factory=list)
    requirements: RequirementsCatalogue | None = None
    draft: dict[str, Any] = Field(default_factory=dict)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    optional_decision_choices: dict[str, bool] = Field(default_factory=dict)
    chat_history: list[dict[str, Any]] = Field(default_factory=list)
    last_validation: ValidationSnapshot | None = None
    validation_attempt_fingerprints: list[str] = Field(default_factory=list)
    automatic_repair_attempts: int = 0
    pending_yaml: str | None = None
    pending_yaml_fingerprint: str | None = None
    last_valid_rendered_yaml: str | None = None
    last_valid_yaml_fingerprint: str | None = None

    def invalidate_current_result(self) -> None:
        self.last_validation = None
        self.pending_yaml = None
        self.pending_yaml_fingerprint = None

    def compact_context(self, max_automatic_repairs: int) -> dict[str, Any]:
        requirements: dict[str, Any] | None = None
        if self.requirements:
            requirements = {
                "fingerprint": self.requirements.fingerprint,
                "requiredPaths": self.requirements.required_paths,
                "optionalDecisions": [
                    decision.model_dump(mode="json")
                    for decision in self.requirements.optional_decisions
                ],
                "fieldCatalog": [
                    field.model_dump(mode="json")
                    for field in self.requirements.field_catalog
                ],
            }
        return {
            "conversationId": self.conversation_id,
            "revision": self.revision,
            "sourceType": self.source_type,
            "targetLayers": self.target_layers,
            "draft": self.draft,
            "requirements": requirements,
            "optionalDecisionChoices": self.optional_decision_choices,
            "lastValidation": (
                self.last_validation.result.model_dump(mode="json")
                if self.last_validation
                else None
            ),
            "automaticRepairAttempts": self.automatic_repair_attempts,
            "maxAutomaticRepairAttempts": max_automatic_repairs,
            "hasPendingYaml": self.pending_yaml is not None,
            "pendingYamlFingerprint": self.pending_yaml_fingerprint,
            "hasLastValidYaml": self.last_valid_rendered_yaml is not None,
        }
