from collections import defaultdict

from adcm.domain.contract import ContractState
from adcm.domain.mutations import MutationCommand, MutationOperation
from adcm.domain.proposals import Proposal, ProposalAction, ProposalDecision, ProposalMode
from adcm.domain.provenance import AUTHORITY, ValueSource

from .json_pointer import exists, get


class ProposalConflict(RuntimeError):
    pass


class ProposalReconciler:
    AUTOMATIC_SOURCES = {
        ValueSource.USER_RULE,
        ValueSource.APP_RULE,
        ValueSource.FORGE_ENRICHMENT,
        ValueSource.FORGE_DEFAULT,
    }

    def reconcile(self, state: ContractState, proposals: list[Proposal]) -> tuple[list[MutationCommand], list[ProposalDecision]]:
        grouped: dict[str, list[Proposal]] = defaultdict(list)
        for proposal in proposals:
            grouped[proposal.path].append(proposal)

        commands: list[MutationCommand] = []
        decisions: list[ProposalDecision] = []

        paths = set(grouped) | {
            path for path, provenance in state.provenance.items() if provenance.source in self.AUTOMATIC_SOURCES
        }
        for path in sorted(paths):
            candidates = grouped.get(path, [])
            current_provenance = state.provenance.get(path)
            if current_provenance and current_provenance.source == ValueSource.USER_EXPLICIT:
                decisions.append(ProposalDecision(path=path, action=ProposalAction.KEEP_CURRENT, reason="explicit user value wins"))
                continue

            winner = self._winner(candidates)
            current_exists = exists(state.document, path)

            if winner is None:
                if current_exists and current_provenance and current_provenance.source in self.AUTOMATIC_SOURCES:
                    commands.append(
                        MutationCommand(
                            operation=MutationOperation.REMOVE,
                            path=path,
                            source=ValueSource.SYSTEM,
                            producer_id="proposal_reconciler",
                            reason="derived producer is no longer active",
                        )
                    )
                    decisions.append(ProposalDecision(path=path, action=ProposalAction.REMOVE_STALE, reason="producer inactive"))
                continue

            if current_exists and current_provenance:
                producer_still_active = any(p.producer_id == current_provenance.producer_id for p in candidates)
                if producer_still_active and AUTHORITY[current_provenance.source] > AUTHORITY[winner.source]:
                    decisions.append(ProposalDecision(path=path, action=ProposalAction.KEEP_CURRENT, proposal_id=winner.id, reason="current value has higher authority"))
                    continue

            current_value = get(state.document, path) if current_exists else None
            if winner.mode == ProposalMode.ENSURE_PRESENT and current_exists:
                decisions.append(ProposalDecision(path=path, action=ProposalAction.KEEP_CURRENT, proposal_id=winner.id, reason="activation target already exists"))
                continue
            if current_exists and current_value == winner.value and current_provenance and current_provenance.producer_id == winner.producer_id:
                decisions.append(ProposalDecision(path=path, action=ProposalAction.KEEP_CURRENT, proposal_id=winner.id, reason="already applied"))
                continue

            commands.append(
                MutationCommand(
                    operation=MutationOperation.REPLACE if current_exists else MutationOperation.ADD,
                    path=path,
                    value=winner.value,
                    source=winner.source,
                    producer_id=winner.producer_id,
                    derived_from=winner.derived_from,
                    reason=winner.reason,
                )
            )
            decisions.append(ProposalDecision(path=path, action=ProposalAction.APPLY, proposal_id=winner.id, reason="winning proposal"))

        return commands, decisions

    def _winner(self, proposals: list[Proposal]) -> Proposal | None:
        if not proposals:
            return None
        ranked = sorted(
            proposals,
            key=lambda item: (AUTHORITY[item.source], item.specificity, item.priority),
            reverse=True,
        )
        winner = ranked[0]
        top_key = (AUTHORITY[winner.source], winner.specificity, winner.priority)
        tied = [p for p in ranked if (AUTHORITY[p.source], p.specificity, p.priority) == top_key]
        differing = {repr(p.value) for p in tied}
        if len(differing) > 1:
            ids = ", ".join(p.producer_id for p in tied)
            raise ProposalConflict(f"conflicting rules for {winner.path}: {ids}")
        return winner
