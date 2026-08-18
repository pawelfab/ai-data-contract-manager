from __future__ import annotations

from adcm.application.candidate_resolver import CandidateResolver
from adcm.application.capability_router import CapabilityRouter
from adcm.application.draft_projector import DraftProjector
from adcm.application.preference_expander import PreferenceExpander
from adcm.application.signal_binder import SignalBinder
from adcm.domain.models import (
    CapabilityResult,
    CapabilityStatus,
    CandidateScope,
    ContractInput,
    ConversationState,
    EvaluationStatus,
    Evidence,
    EvidenceKind,
    ExternalCandidate,
    FinalValidationReceipt,
    FinalValidationStatus,
    ValueCandidate,
    WorkflowOutcome,
    WorkflowOutcomeStatus,
)
from adcm.ports.contract_forge import ContractForgePort


class WorkflowRunner:
    """Deterministic fast-forward loop. ADCM owns state; Forge is stateless."""

    def __init__(
        self,
        contract_forge: ContractForgePort,
        capability_router: CapabilityRouter | None = None,
        max_steps: int = 50,
    ) -> None:
        self.contract_forge = contract_forge
        self.capability_router = capability_router
        self.max_steps = max_steps
        self.signal_binder = SignalBinder()
        self.preference_expander = PreferenceExpander()
        self.resolver = CandidateResolver()
        self.projector = DraftProjector()

    @staticmethod
    def _candidate_key(candidate: ValueCandidate) -> tuple:
        return (
            candidate.path,
            repr(candidate.value),
            candidate.origin,
            candidate.scope,
            candidate.rule_id,
            candidate.source_signal_id,
            candidate.source_preference_id,
        )

    def _append_unique_candidates(self, state: ConversationState, candidates: list[ValueCandidate]) -> bool:
        existing = {self._candidate_key(c) for c in state.value_candidates}
        changed = False
        for candidate in candidates:
            key = self._candidate_key(candidate)
            if key in existing:
                continue
            state.candidate_sequence += 1
            candidate.sequence = state.candidate_sequence
            state.value_candidates.append(candidate)
            existing.add(key)
            changed = True
        return changed

    def _convert_external_candidate(self, state: ConversationState, item: ExternalCandidate) -> ValueCandidate:
        evidence_ids = []
        if item.evidence is not None:
            state.evidence.append(item.evidence)
            evidence_ids.append(item.evidence.id)
        elif item.reason:
            kind_map = {
                "mcp_enrichment": EvidenceKind.MCP_ENRICHMENT,
                "mcp_default": EvidenceKind.MCP_DEFAULT,
                "mcp_derived": EvidenceKind.MCP_DERIVED,
            }
            evidence = Evidence(
                kind=kind_map.get(item.origin.value, EvidenceKind.MCP_RULE),
                content={"reason": item.reason, "rule_id": item.rule_id, "scope": item.scope},
            )
            state.evidence.append(evidence)
            evidence_ids.append(evidence.id)
        return ValueCandidate(
            path=item.path,
            value=item.value,
            origin=item.origin,
            evidence_ids=evidence_ids,
            priority=item.priority,
            scope=item.scope or CandidateScope.GENERIC,
            rule_id=item.rule_id,
            created_revision=state.revision,
            reason=item.reason,
        )

    async def _resolve_capabilities(self, requests, state: ConversationState) -> tuple[bool, bool]:
        """Returns (resolved_any, blocked_external)."""
        if not requests:
            return False, False
        if self.capability_router is None:
            return False, True

        resolved_any = False
        for request in requests:
            if any(result.request_id == request.request_id for result in state.workflow.capability_results):
                continue
            if not self.capability_router.can_execute(request.capability):
                return resolved_any, True
            try:
                payload = await self.capability_router.execute(request.capability, request.args)
            except Exception as exc:  # adapter boundary: failure is recorded, not hidden
                state.workflow.capability_results.append(
                    CapabilityResult(
                        request_id=request.request_id,
                        capability=request.capability,
                        status=CapabilityStatus.UNAVAILABLE,
                        error=str(exc),
                    )
                )
                return resolved_any, True
            state.workflow.capability_results.append(
                CapabilityResult(
                    request_id=request.request_id,
                    capability=request.capability,
                    status=CapabilityStatus.SUCCESS,
                    result=payload,
                )
            )
            resolved_any = True
        return resolved_any, False

    async def run_until_stable(self, state: ConversationState) -> WorkflowOutcome:
        start_hash = state.contract_draft.canonical_hash()

        for _ in range(self.max_steps):
            expected_revision = (
                state.workflow.current_schema_view.schema_revision
                if state.workflow.current_schema_view is not None
                else None
            )
            evaluation = await self.contract_forge.evaluate_draft(
                ContractInput(
                    draft=state.contract_draft.values,
                    capability_results=state.workflow.capability_results,
                    expected_schema_revision=expected_revision,
                )
            )

            # Replace the current view. Never accumulate allowed paths across branch changes.
            state.workflow.current_schema_view = evaluation.schema_view
            state.workflow.current_stage = evaluation.schema_view.stage_id
            state.workflow.pending_requirements = evaluation.requirements
            state.workflow.last_evaluation_status = evaluation.status

            if evaluation.status == EvaluationStatus.INVALID:
                return WorkflowOutcome(
                    status=WorkflowOutcomeStatus.INVALID,
                    draft_changed=state.contract_draft.canonical_hash() != start_hash,
                    draft_hash=state.contract_draft.canonical_hash(),
                    schema_revision=evaluation.schema_view.schema_revision,
                )

            new_candidates: list[ValueCandidate] = []
            new_candidates.extend(
                self.signal_binder.bind(state.signals, evaluation.schema_view.allowed_paths)
            )
            new_candidates.extend(
                self.preference_expander.expand(state.preferences, evaluation.schema_view.allowed_paths)
            )
            new_candidates.extend(
                self._convert_external_candidate(state, candidate) for candidate in evaluation.candidates
            )

            changed = self._append_unique_candidates(state, new_candidates)
            previous_resolved = {path: value.value for path, value in state.resolved_values.items()}
            state.resolved_values = self.resolver.resolve(state.value_candidates)
            current_resolved = {path: value.value for path, value in state.resolved_values.items()}
            if current_resolved != previous_resolved:
                changed = True

            new_draft = self.projector.project(
                state.resolved_values,
                evaluation.schema_view,
                state.revision,
            )
            if new_draft.values != state.contract_draft.values:
                changed = True
            state.contract_draft = new_draft

            missing = [
                requirement.path
                for requirement in evaluation.requirements
                if requirement.required and requirement.path not in state.resolved_values
            ]

            capabilities_resolved, blocked = await self._resolve_capabilities(
                evaluation.capability_requests, state
            )
            if blocked:
                return WorkflowOutcome(
                    status=WorkflowOutcomeStatus.BLOCKED_EXTERNAL,
                    missing_paths=missing,
                    draft_changed=state.contract_draft.canonical_hash() != start_hash,
                    draft_hash=state.contract_draft.canonical_hash(),
                    schema_revision=evaluation.schema_view.schema_revision,
                    reason="required external capability is unavailable",
                )
            if capabilities_resolved:
                continue

            if evaluation.status == EvaluationStatus.COMPLETE:
                final = await self.contract_forge.validate_final(
                    ContractInput(
                        draft=state.contract_draft.values,
                        capability_results=state.workflow.capability_results,
                        expected_schema_revision=evaluation.schema_view.schema_revision,
                    )
                )
                if final.status == FinalValidationStatus.VALID:
                    draft_hash = state.contract_draft.canonical_hash()
                    receipt = FinalValidationReceipt(
                        status=final.status,
                        draft_hash=draft_hash,
                        schema_revision=final.schema_revision,
                    )
                    return WorkflowOutcome(
                        status=WorkflowOutcomeStatus.COMPLETE,
                        draft_changed=draft_hash != start_hash,
                        draft_hash=draft_hash,
                        schema_revision=final.schema_revision,
                        final_validation=receipt,
                    )
                if final.status == FinalValidationStatus.INVALID:
                    return WorkflowOutcome(
                        status=WorkflowOutcomeStatus.INVALID,
                        draft_changed=state.contract_draft.canonical_hash() != start_hash,
                        draft_hash=state.contract_draft.canonical_hash(),
                        schema_revision=final.schema_revision,
                    )

                capabilities_resolved, blocked = await self._resolve_capabilities(
                    final.capability_requests, state
                )
                if capabilities_resolved:
                    continue
                return WorkflowOutcome(
                    status=WorkflowOutcomeStatus.BLOCKED_EXTERNAL,
                    draft_changed=state.contract_draft.canonical_hash() != start_hash,
                    draft_hash=state.contract_draft.canonical_hash(),
                    schema_revision=final.schema_revision,
                    reason="final validation deferred on external dependency",
                )

            if missing:
                return WorkflowOutcome(
                    status=WorkflowOutcomeStatus.WAITING_FOR_USER,
                    missing_paths=missing,
                    draft_changed=state.contract_draft.canonical_hash() != start_hash,
                    draft_hash=state.contract_draft.canonical_hash(),
                    schema_revision=evaluation.schema_view.schema_revision,
                )

            if not changed:
                return WorkflowOutcome(
                    status=WorkflowOutcomeStatus.FAILED,
                    draft_changed=state.contract_draft.canonical_hash() != start_hash,
                    draft_hash=state.contract_draft.canonical_hash(),
                    schema_revision=evaluation.schema_view.schema_revision,
                    reason=f"workflow made no progress at stage {evaluation.schema_view.stage_id!r}",
                )

        return WorkflowOutcome(
            status=WorkflowOutcomeStatus.FAILED,
            draft_changed=state.contract_draft.canonical_hash() != start_hash,
            draft_hash=state.contract_draft.canonical_hash(),
            schema_revision=(
                state.workflow.current_schema_view.schema_revision
                if state.workflow.current_schema_view
                else None
            ),
            reason="workflow exceeded max_steps",
        )

    async def run(self, state: ConversationState) -> WorkflowOutcome:
        """Compatibility alias used by ChatService."""
        return await self.run_until_stable(state)
