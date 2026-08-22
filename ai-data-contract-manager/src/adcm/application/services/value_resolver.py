from __future__ import annotations

from copy import deepcopy
from typing import Any

from adcm.application.ports.forge import Requirement, SuggestedValue
from adcm.application.ports.llm import Candidate
from adcm.application.services.candidate_decision import (
    CandidateDecision,
    CandidateDecisionStatus,
    CandidateOutcome,
)
from adcm.domain.contract.path import JsonPointerError, exists_pointer, get_pointer, set_pointer
from adcm.domain.contract.state import ContractState
from adcm.domain.contract.value import Authority, DerivedValue, Provenance
from adcm.domain.evidence.models import EvidenceItem


_AUTHORITY_RANK = {
    Authority.DEFAULT: 0,
    Authority.OBSERVED_CONVENTION: 100,
    Authority.SYSTEM_RULE: 200,
    Authority.USER_REFERENCED: 300,
    Authority.USER_DIRECT: 400,
}


class ValueResolver:
    def apply_suggestions(self, state: ContractState, suggestions: list[SuggestedValue]) -> bool:
        """Recompute derived state from the current Forge result; never accumulate stale rules."""

        user_paths = set(state.latest_user_values())
        user_document = state.user_document()
        accepted: dict[str, DerivedValue] = {}
        derived_doc: dict[str, Any] = {}

        # Higher-priority structural suggestion wins before a lower-priority conflicting one.
        for suggestion in sorted(suggestions, key=lambda x: x.priority, reverse=True):
            if suggestion.path in user_paths:
                continue
            if _destroys_container(user_document, suggestion.path, suggestion.value):
                continue
            if _destroys_container(derived_doc, suggestion.path, suggestion.value):
                continue
            try:
                trial_derived = set_pointer(derived_doc, suggestion.path, suggestion.value)
                trial_effective = trial_derived
                for event in state.latest_user_values().values():
                    trial_effective = set_pointer(trial_effective, event.path, event.value)
            except JsonPointerError:
                continue
            derived_doc = trial_derived
            accepted[suggestion.path] = DerivedValue(
                path=suggestion.path,
                value=suggestion.value,
                source=suggestion.source,
                priority=suggestion.priority,
                provenance=Provenance(
                    source_type="contract_forge",
                    source_ref=suggestion.source_ref,
                    rule_id=suggestion.rule_id,
                ),
            )

        return state.replace_derived(accepted)

    def apply_candidates(
        self,
        state: ContractState,
        candidates: list[Candidate],
        evidence: list[EvidenceItem],
        requirements: list[Requirement],
        min_confidence: float = 0.80,
    ) -> CandidateOutcome:
        decisions: list[CandidateDecision] = []
        changed = False
        evidence_by_id = {item.id: item for item in evidence}

        for candidate in candidates:
            source = evidence_by_id.get(candidate.evidence_id)
            if source is None:
                decisions.append(_decision(candidate, CandidateDecisionStatus.REJECTED, "unknown_evidence"))
                continue
            if candidate.confidence < min_confidence:
                decisions.append(_decision(candidate, CandidateDecisionStatus.REJECTED, "low_confidence"))
                continue

            current_document = state.effective_document()
            matching = _matching_requirement(candidate.path, requirements)
            if matching is None and not exists_pointer(current_document, candidate.path):
                decisions.append(_decision(candidate, CandidateDecisionStatus.REJECTED, "unknown_path"))
                continue
            if matching and matching.path != candidate.path and matching.expected_type not in {"object", "array"}:
                decisions.append(_decision(candidate, CandidateDecisionStatus.REJECTED, "unknown_path"))
                continue
            if matching and matching.path == candidate.path and not _type_matches(candidate.value, matching.expected_type):
                decisions.append(_decision(candidate, CandidateDecisionStatus.REJECTED, "invalid_type"))
                continue
            if _destroys_container(current_document, candidate.path, candidate.value):
                decisions.append(_decision(candidate, CandidateDecisionStatus.REJECTED, "destroys_container"))
                continue

            old = state.latest_user_values().get(candidate.path)
            if old and _AUTHORITY_RANK[old.authority] > _AUTHORITY_RANK[source.authority]:
                decisions.append(
                    _decision(candidate, CandidateDecisionStatus.SHADOWED, "shadowed_by_higher_authority")
                )
                continue

            trial = state.model_copy(deep=True)
            trial.set_user(
                candidate.path,
                candidate.value,
                authority=source.authority,
                provenance=Provenance(
                    source_type=source.source_type,
                    source_ref=source.source_ref,
                    evidence_id=source.id,
                ),
            )
            try:
                trial.effective_document()
            except JsonPointerError:
                decisions.append(_decision(candidate, CandidateDecisionStatus.REJECTED, "structural_conflict"))
                continue

            actual_change = old is None or old.value != candidate.value or old.authority != source.authority
            if actual_change:
                state.set_user(
                    candidate.path,
                    candidate.value,
                    authority=source.authority,
                    provenance=Provenance(
                        source_type=source.source_type,
                        source_ref=source.source_ref,
                        evidence_id=source.id,
                    ),
                )
                changed = True
            decisions.append(_decision(candidate, CandidateDecisionStatus.ACCEPTED, None))

        return CandidateOutcome(decisions=decisions, changed=changed)


def _matching_requirement(path: str, requirements: list[Requirement]) -> Requirement | None:
    exact = next((r for r in requirements if r.path == path), None)
    if exact:
        return exact
    candidates = [r for r in requirements if path.startswith(r.path.rstrip("/") + "/")]
    return max(candidates, key=lambda r: len(r.path), default=None)


def _destroys_container(document: dict[str, Any], path: str, value: Any) -> bool:
    marker = object()
    existing = get_pointer(document, path, marker)
    if existing is marker:
        return False
    if isinstance(existing, dict):
        return not isinstance(value, dict)
    if isinstance(existing, list):
        return not isinstance(value, list)
    return False


def _type_matches(value: Any, expected_type: str | None) -> bool:
    if not expected_type:
        return True
    checks = {
        "string": lambda x: isinstance(x, str),
        "integer": lambda x: isinstance(x, int) and not isinstance(x, bool),
        "number": lambda x: isinstance(x, (int, float)) and not isinstance(x, bool),
        "boolean": lambda x: isinstance(x, bool),
        "object": lambda x: isinstance(x, dict),
        "array": lambda x: isinstance(x, list),
        "null": lambda x: x is None,
    }
    check = checks.get(expected_type)
    return True if check is None else check(value)


def _decision(candidate: Candidate, status: CandidateDecisionStatus, reason: str | None) -> CandidateDecision:
    return CandidateDecision(candidate=candidate, status=status, reason=reason)
