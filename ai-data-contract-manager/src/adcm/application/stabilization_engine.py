from adcm.domain.contract import ContractState
from adcm.domain.forge import ForgeAnalysis
from adcm.domain.mutations import MutationCommand, MutationOperation
from adcm.domain.proposals import Proposal
from adcm.domain.provenance import ValueSource
from adcm.domain.rules import RulesDocument
from adcm.domain.turn import StabilizationReport
from adcm.ports.forge import ContractForgePort

from .document_engine import DocumentEngine
from .proposal_reconciler import ProposalReconciler
from .rules_engine import ConventionRulesEngine


class StabilizationEngine:
    def __init__(
        self,
        forge: ContractForgePort,
        document_engine: DocumentEngine,
        rules_engine: ConventionRulesEngine,
        proposal_reconciler: ProposalReconciler,
        *,
        max_rounds: int = 8,
    ) -> None:
        self.forge = forge
        self.document_engine = document_engine
        self.rules_engine = rules_engine
        self.proposal_reconciler = proposal_reconciler
        self.max_rounds = max_rounds

    async def stabilize(self, state: ContractState, rules: RulesDocument) -> tuple[ForgeAnalysis, StabilizationReport]:
        all_decisions: list[dict] = []
        foreign_removed: list[str] = []

        for round_no in range(1, self.max_rounds + 1):
            analysis = await self.forge.analyze(state.document)

            if analysis.foreign:
                cleanup = self._foreign_cleanup_commands(analysis)
                self.document_engine.apply(state, cleanup)
                foreign_removed.extend(item.path for item in analysis.foreign)
                continue

            proposals = self._forge_proposals(analysis)
            proposals.extend(self.rules_engine.evaluate(rules, state, analysis))
            commands, decisions = self.proposal_reconciler.reconcile(state, proposals)
            all_decisions.extend(decision.model_dump(mode="json") for decision in decisions)
            if not commands:
                return analysis, StabilizationReport(
                    rounds=round_no,
                    converged=True,
                    proposal_decisions=all_decisions,
                    foreign_removed=foreign_removed,
                )
            self.document_engine.apply(state, commands)

        analysis = await self.forge.analyze(state.document)
        return analysis, StabilizationReport(
            rounds=self.max_rounds,
            converged=False,
            proposal_decisions=all_decisions,
            foreign_removed=foreign_removed,
        )

    @staticmethod
    def _forge_proposals(analysis: ForgeAnalysis) -> list[Proposal]:
        result: list[Proposal] = []
        for proposal in analysis.proposals:
            source = (
                ValueSource.FORGE_ENRICHMENT
                if proposal.origin == "enrichment"
                else ValueSource.FORGE_DEFAULT
            )
            result.append(
                Proposal(
                    id=f"forge:{proposal.id}",
                    path=proposal.path,
                    value=proposal.value,
                    source=source,
                    producer_id=proposal.rule_id or proposal.id,
                    reason=proposal.reason,
                    derived_from=proposal.derived_from,
                )
            )
        return result

    @staticmethod
    def _foreign_cleanup_commands(analysis: ForgeAnalysis) -> list[MutationCommand]:
        # Deepest paths first, so removing a child never invalidates a later parent lookup.
        items = sorted(analysis.foreign, key=lambda item: (item.path.count("/"), item.path), reverse=True)
        return [
            MutationCommand(
                operation=MutationOperation.REMOVE,
                path=item.path,
                source=ValueSource.SYSTEM,
                producer_id="forge_foreign_cleanup",
                reason=f"foreign: {item.reason}",
            )
            for item in items
        ]
