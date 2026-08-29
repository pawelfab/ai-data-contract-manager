from time import perf_counter
from typing import TYPE_CHECKING, Any

from adcm.domain.contract import ContractState
from adcm.domain.forge import ForgeAnalysis
from adcm.domain.mutations import MutationCommand, MutationOperation
from adcm.domain.proposals import Proposal
from adcm.domain.provenance import ValueSource
from adcm.domain.rules import RulesDocument
from adcm.domain.turn import StabilizationReport
from adcm.ports.forge import ContractForgePort

from .document_engine import DocumentEngine
from .json_pointer import exists, get
from .proposal_reconciler import ProposalReconciler
from .rules_engine import ConventionRulesEngine

if TYPE_CHECKING:
    from adcm.application.observability.session_audit_recorder import BoundTurnAuditRecorder


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

    async def stabilize(
        self,
        state: ContractState,
        rules: RulesDocument,
        *,
        correlation_id: str | None = None,
        audit: "BoundTurnAuditRecorder | None" = None,
    ) -> tuple[ForgeAnalysis, StabilizationReport]:
        all_decisions: list[dict] = []
        foreign_removed: list[str] = []

        for round_no in range(1, self.max_rounds + 1):
            revision_before = state.revision
            self._record(
                audit,
                "stabilization.round.started",
                {"round": round_no, "contract_revision": revision_before},
            )
            analysis = await self._analyze(
                state,
                round_no=round_no,
                correlation_id=correlation_id,
                audit=audit,
            )

            if analysis.foreign:
                cleanup = self._foreign_cleanup_commands(analysis)
                mutation_events = self.document_engine.apply(state, cleanup)
                self._record_mutations(audit, mutation_events)
                foreign_removed.extend(item.path for item in analysis.foreign)
                self._record(
                    audit,
                    "stabilization.round.completed",
                    {
                        "round": round_no,
                        "changed": bool(mutation_events),
                        "revision_before": revision_before,
                        "revision_after": state.revision,
                        "foreign_removed": [item.path for item in analysis.foreign],
                    },
                )
                continue

            forge_proposals = self._forge_proposals(analysis)
            rule_proposals = self.rules_engine.evaluate(rules, state, analysis)
            for proposal in forge_proposals:
                self._record(audit, "forge.proposal.received", proposal.model_dump(mode="json"))
            for proposal in rule_proposals:
                self._record(audit, "rule.proposal.generated", proposal.model_dump(mode="json"))

            proposals = [*forge_proposals, *rule_proposals]
            commands, decisions = self.proposal_reconciler.reconcile(state, proposals)
            all_decisions.extend(decision.model_dump(mode="json") for decision in decisions)
            self._record_proposal_decisions(audit, state, proposals, decisions)
            if not commands:
                self._record(
                    audit,
                    "stabilization.round.completed",
                    {
                        "round": round_no,
                        "changed": False,
                        "revision_before": revision_before,
                        "revision_after": state.revision,
                    },
                )
                self._record(
                    audit,
                    "stabilization.completed",
                    {"rounds": round_no, "converged": True, "final_revision": state.revision},
                )
                return analysis, StabilizationReport(
                    rounds=round_no,
                    converged=True,
                    proposal_decisions=all_decisions,
                    foreign_removed=foreign_removed,
                )
            mutation_events = self.document_engine.apply(state, commands)
            self._record_mutations(audit, mutation_events)
            self._record(
                audit,
                "stabilization.round.completed",
                {
                    "round": round_no,
                    "changed": bool(mutation_events),
                    "revision_before": revision_before,
                    "revision_after": state.revision,
                },
            )

        analysis = await self._analyze(
            state,
            round_no=self.max_rounds + 1,
            correlation_id=correlation_id,
            audit=audit,
            phase="final_validation",
        )
        self._record(
            audit,
            "stabilization.completed",
            {"rounds": self.max_rounds, "converged": False, "final_revision": state.revision},
        )
        return analysis, StabilizationReport(
            rounds=self.max_rounds,
            converged=False,
            proposal_decisions=all_decisions,
            foreign_removed=foreign_removed,
        )

    async def _analyze(
        self,
        state: ContractState,
        *,
        round_no: int,
        correlation_id: str | None,
        audit: "BoundTurnAuditRecorder | None",
        phase: str | None = None,
    ) -> ForgeAnalysis:
        started_data: dict[str, Any] = {"round": round_no, "contract_revision": state.revision}
        if phase is not None:
            started_data["phase"] = phase
        self._record(audit, "forge.analysis.started", started_data)
        started = perf_counter()
        if correlation_id is None:
            analysis = await self.forge.analyze(state.document)
        else:
            analysis = await self.forge.analyze(state.document, correlation_id=correlation_id)
        duration_ms = (perf_counter() - started) * 1000
        completed_data = analysis.model_dump(mode="json")
        completed_data.update(started_data)
        completed_data["duration_ms"] = duration_ms
        self._record(audit, "forge.analysis.completed", completed_data)
        return analysis

    @classmethod
    def _record_mutations(cls, audit: "BoundTurnAuditRecorder | None", events: list) -> None:
        for event in events:
            cls._record(audit, "mutation.applied", event.model_dump(mode="json"))

    @classmethod
    def _record_proposal_decisions(cls, audit, state, proposals, decisions) -> None:
        proposals_by_id = {proposal.id: proposal for proposal in proposals}
        for decision in decisions:
            data = decision.model_dump(mode="json")
            proposal = proposals_by_id.get(decision.proposal_id)
            if proposal is not None:
                data.update(
                    {
                        "proposed_value": proposal.value,
                        "proposal_source": proposal.source.value,
                        "producer_id": proposal.producer_id,
                    }
                )
            current_exists = exists(state.document, decision.path)
            data["current_exists"] = current_exists
            data["current_value"] = get(state.document, decision.path) if current_exists else None
            provenance = state.provenance.get(decision.path)
            data["current_source"] = provenance.source.value if provenance is not None else None
            cls._record(audit, "proposal.decision", data)

    @staticmethod
    def _record(audit: "BoundTurnAuditRecorder | None", event_type: str, data: dict) -> None:
        if audit is not None:
            audit.record(event_type, data)

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
