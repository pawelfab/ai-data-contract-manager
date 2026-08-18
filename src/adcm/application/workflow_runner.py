from __future__ import annotations

from adcm.application.candidate_resolver import CandidateResolver
from adcm.application.draft_projector import DraftProjector
from adcm.application.preference_expander import PreferenceExpander
from adcm.application.signal_binder import SignalBinder
from adcm.domain.models import (
    ConversationState,
    Evidence,
    EvidenceKind,
    ExternalCandidate,
    ValueCandidate,
)
from adcm.ports.contract_forge import ContractForgePort


class WorkflowResult:
    def __init__(self, *, needs_user_input: bool, missing_paths: list[str], complete: bool):
        self.needs_user_input = needs_user_input
        self.missing_paths = missing_paths
        self.complete = complete


class WorkflowRunner:
    """Deterministic fast-forward loop over Contract Forge stages."""

    def __init__(self, contract_forge: ContractForgePort, max_steps: int = 50):
        self.contract_forge = contract_forge
        self.max_steps = max_steps
        self.signal_binder = SignalBinder()
        self.preference_expander = PreferenceExpander()
        self.resolver = CandidateResolver()
        self.projector = DraftProjector()

    @staticmethod
    def _candidate_key(candidate: ValueCandidate) -> tuple:
        return (candidate.path, repr(candidate.value), candidate.origin, tuple(candidate.evidence_ids))

    def _append_unique_candidates(self, state: ConversationState, candidates: list[ValueCandidate]) -> bool:
        existing = {self._candidate_key(c) for c in state.value_candidates}
        changed = False
        for candidate in candidates:
            key = self._candidate_key(candidate)
            if key not in existing:
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
                content=item.reason,
            )
            state.evidence.append(evidence)
            evidence_ids.append(evidence.id)
        return ValueCandidate(
            path=item.path,
            value=item.value,
            origin=item.origin,
            evidence_ids=evidence_ids,
            priority=item.priority,
            reason=item.reason,
        )

    async def run(self, state: ConversationState) -> WorkflowResult:
        for _ in range(self.max_steps):
            known = {path: value.value for path, value in state.resolved_values.items()}
            bundle = await self.contract_forge.next_requirements(known)

            state.workflow.current_stage = bundle.stage_id
            state.workflow.allowed_paths.update(bundle.allowed_path_set)
            state.workflow.pending_requirements = bundle.requirements
            state.workflow.complete = bundle.complete

            new_candidates: list[ValueCandidate] = []
            new_candidates.extend(self.signal_binder.bind(state.signals, bundle.allowed_paths))
            new_candidates.extend(self.preference_expander.expand(state.preferences, bundle.allowed_paths))
            new_candidates.extend(self._convert_external_candidate(state, c) for c in bundle.candidates)

            changed = self._append_unique_candidates(state, new_candidates)
            previous = {k: v.value for k, v in state.resolved_values.items()}
            state.resolved_values = self.resolver.resolve(state.value_candidates)
            current = {k: v.value for k, v in state.resolved_values.items()}
            if current != previous:
                changed = True

            state.contract_draft = self.projector.project(
                state.resolved_values,
                state.workflow.allowed_paths,
                state.revision,
            )

            missing = [
                req.path
                for req in bundle.requirements
                if req.required and req.path not in state.resolved_values
            ]

            if bundle.complete:
                return WorkflowResult(needs_user_input=False, missing_paths=[], complete=True)
            if missing:
                return WorkflowResult(needs_user_input=True, missing_paths=missing, complete=False)
            if not changed:
                raise RuntimeError(
                    f"Workflow made no progress at stage {bundle.stage_id!r}; refusing infinite loop"
                )

        raise RuntimeError("Workflow exceeded max_steps")
