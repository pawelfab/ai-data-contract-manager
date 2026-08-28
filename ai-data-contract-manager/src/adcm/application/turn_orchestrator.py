from adcm.domain.session import TurnSnapshot
from adcm.domain.turn import TurnOutcome
from adcm.ports.forge import ContractForgePort
from adcm.ports.intent import IntentResolverPort
from adcm.ports.response import ResponseComposerPort
from adcm.ports.rules_repository import RulesRepositoryPort
from adcm.ports.session_repository import SessionRepositoryPort

from .candidate_policy import CandidatePolicy
from .document_engine import DocumentEngine
from .external_check_coordinator import ExternalCheckCoordinator
from .stabilization_engine import StabilizationEngine


class TurnOrchestrator:
    def __init__(
        self,
        *,
        sessions: SessionRepositoryPort,
        forge: ContractForgePort,
        intent: IntentResolverPort,
        rules: RulesRepositoryPort,
        response: ResponseComposerPort,
        candidate_policy: CandidatePolicy,
        document_engine: DocumentEngine,
        stabilization: StabilizationEngine,
        external_checks: ExternalCheckCoordinator,
    ) -> None:
        self.sessions = sessions
        self.forge = forge
        self.intent = intent
        self.rules = rules
        self.response = response
        self.candidate_policy = candidate_policy
        self.document_engine = document_engine
        self.stabilization = stabilization
        self.external_checks = external_checks

    async def run_turn(self, session_id: str, user_message: str) -> TurnOutcome:
        session = await self.sessions.get_or_create(session_id)
        log_start = len(session.contract.mutation_log)

        definition = await self.forge.describe()
        resolution = await self.intent.resolve(
            user_message,
            document=session.contract.document,
            definition=definition,
        )
        user_commands = self.candidate_policy.decide(session.contract, resolution.candidates)
        self.document_engine.apply(session.contract, user_commands)

        effective_rules = await self.rules.load(session_id)
        forge_analysis, stabilization_report = await self.stabilization.stabilize(session.contract, effective_rules)
        external_status = await self.external_checks.run(document=session.contract.document)

        session.turn_no += 1
        session.snapshots.append(
            TurnSnapshot(
                turn_no=session.turn_no,
                revision=session.contract.revision,
                document=session.contract.snapshot_document(),
            )
        )
        new_events = session.contract.mutation_log[log_start:]

        provisional = TurnOutcome(
            session_id=session.session_id,
            turn_no=session.turn_no,
            message="",
            document=session.contract.snapshot_document(),
            forge=forge_analysis,
            external_checks=external_status,
            new_events=new_events,
            stabilization=stabilization_report,
        )
        message = await self.response.compose(provisional)
        outcome = provisional.model_copy(update={"message": message})
        await self.sessions.save(session)
        return outcome
