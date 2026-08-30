from copy import deepcopy

import pytest

from adcm.adapters.response_basic import BasicResponseComposer
from adcm.adapters.session_memory import InMemorySessionRepository
from adcm.application.candidate_policy import CandidatePolicy, CandidatePolicyResult
from adcm.application.document_engine import DocumentEngine
from adcm.application.external_check_coordinator import ExternalCheckCoordinator
from adcm.application.observability.app_log_recorder import AppLogRecorder
from adcm.application.observability.session_audit_recorder import SessionAuditRecorder
from adcm.application.proposal_reconciler import ProposalReconciler
from adcm.application.rules_engine import ConventionRulesEngine
from adcm.application.stabilization_engine import StabilizationEngine
from adcm.application.turn_orchestrator import TurnOrchestrator
from adcm.domain.contract import ContractState
from adcm.domain.forge import ContractStatus, ForgeAnalysis, ForgeDescription
from adcm.domain.mutations import CandidateAction, MutationCandidate, MutationEvent, MutationOperation
from adcm.domain.provenance import ValueProvenance, ValueSource
from adcm.domain.rules import RulesDocument
from adcm.domain.session import SessionState
from adcm.domain.turn import IntentKind, IntentResolution


class CaptureSink:
    def __init__(self) -> None:
        self.events = []

    def emit(self, event) -> None:
        self.events.append(event)


class FakeForge:
    async def describe(self, *, correlation_id: str | None = None) -> ForgeDescription:
        return ForgeDescription(protocol_version="1.0", definition_version="fake")

    async def analyze(self, document: dict, *, correlation_id: str | None = None) -> ForgeAnalysis:
        return ForgeAnalysis(
            protocol_version="1.0",
            definition_version="fake",
            status=ContractStatus(valid=True, complete=True, clean=True),
        )


class FakeIntent:
    def __init__(self, resolutions: dict[str, IntentResolution]) -> None:
        self.resolutions = resolutions

    async def resolve(self, message: str, *, document: dict, definition=None) -> IntentResolution:
        return self.resolutions[message]


class RulesRepository:
    async def load(self, session_id: str) -> RulesDocument:
        return RulesDocument(version="test", rules=[])


def build_orchestrator(
    resolutions: dict[str, IntentResolution],
    candidate_policy: CandidatePolicy | None = None,
):
    audit_sink = CaptureSink()
    app_sink = CaptureSink()
    app_log = AppLogRecorder(app_sink, environment="test")
    audit = SessionAuditRecorder(audit_sink, app_log)
    forge = FakeForge()
    document_engine = DocumentEngine()
    stabilization = StabilizationEngine(
        forge,
        document_engine,
        ConventionRulesEngine(),
        ProposalReconciler(),
    )
    sessions = InMemorySessionRepository()
    orchestrator = TurnOrchestrator(
        sessions=sessions,
        forge=forge,
        intent=FakeIntent(resolutions),
        rules=RulesRepository(),
        response=BasicResponseComposer(),
        candidate_policy=candidate_policy or CandidatePolicy(),
        document_engine=document_engine,
        stabilization=stabilization,
        external_checks=ExternalCheckCoordinator(),
        audit=audit,
        app_log=app_log,
    )
    return orchestrator, sessions, audit_sink


def sample_document() -> dict:
    return {
        "metadata": {
            "sourceSystemGcpId": "sap",
            "id": "sap",
            "version": "1.0.0",
        },
        "source": {"sourceType": "csv", "systemZrodlowy": "sap", "encoding": "UTF-8"},
        "converter": {"outputFilename": "sap_{{data_danych}}.csv"},
    }


async def seed_session(sessions: InMemorySessionRepository, document: dict) -> None:
    output_filename = document["converter"]["outputFilename"]
    await sessions.save(
        SessionState(
            session_id="session-1",
            contract=ContractState(
                document=document,
                provenance={
                    "/converter/outputFilename": ValueProvenance(
                        source=ValueSource.USER_EXPLICIT,
                        producer_id="seed",
                        revision=1,
                    )
                },
                revision=1,
                mutation_log=[
                    MutationEvent(
                        mutation_id="seed",
                        revision_before=0,
                        revision_after=1,
                        operation=MutationOperation.ADD,
                        path="/converter/outputFilename",
                        old_exists=False,
                        new_exists=True,
                        new_value=output_filename,
                        source=ValueSource.USER_EXPLICIT,
                        producer_id="seed",
                    )
                ],
            ),
        )
    )


@pytest.mark.asyncio
async def test_knowledge_query_does_not_mutate_contract() -> None:
    message = "jakie opcje converter dostępne?"
    orchestrator, sessions, audit_sink = build_orchestrator(
        {message: IntentResolution(intent_kind=IntentKind.KNOWLEDGE, knowledge_query="jakie pola i opcje są dostępne w /converter?")}
    )
    await seed_session(sessions, sample_document())
    before = await sessions.get("session-1")
    assert before is not None
    document_before = deepcopy(before.contract.document)
    provenance_before = deepcopy(before.contract.provenance)
    revision_before = before.contract.revision
    mutation_log_before = deepcopy(before.contract.mutation_log)

    outcome = await orchestrator.run_turn("session-1", message)

    after = await sessions.get("session-1")
    assert after is not None
    assert outcome.document == document_before
    assert after.contract.document == document_before
    assert after.contract.provenance == provenance_before
    assert after.contract.revision == revision_before
    assert after.contract.mutation_log == mutation_log_before
    assert not [event for event in audit_sink.events if event.event_type == "candidate.accepted"]
    assert not [
        event
        for event in outcome.new_events
        if event.source == ValueSource.USER_EXPLICIT
    ]
    assert outcome.stabilization.converged is True


@pytest.mark.asyncio
async def test_knowledge_query_can_coexist_with_explicit_mutation() -> None:
    message = "ustaw dataFileId sap_id i powiedz jakie opcje ma converter"
    candidate = MutationCandidate(
        action=CandidateAction.SET,
        path="/metadata/dataFileId",
        value="sap_id",
        confidence=0.99,
        evidence=message,
    )
    orchestrator, sessions, audit_sink = build_orchestrator(
        {
            message: IntentResolution(
                intent_kind=IntentKind.MIXED,
                candidates=[candidate],
                knowledge_query="jakie pola i opcje są dostępne w /converter?",
            )
        }
    )
    await seed_session(sessions, sample_document())

    outcome = await orchestrator.run_turn("session-1", message)

    after = await sessions.get("session-1")
    assert after is not None
    assert outcome.document["metadata"]["dataFileId"] == "sap_id"
    assert after.contract.document == outcome.document
    assert after.contract.revision == 2
    assert after.contract.provenance["/metadata/dataFileId"].source == ValueSource.USER_EXPLICIT
    assert len(outcome.new_events) == 1
    assert outcome.new_events[0].source == ValueSource.USER_EXPLICIT
    assert outcome.new_events[0].path == "/metadata/dataFileId"
    assert outcome.stabilization.converged is True
    assert any(event.event_type == "candidate.accepted" for event in audit_sink.events)
    intent_event = next(event for event in audit_sink.events if event.event_type == "intent.resolved")
    assert intent_event.data["knowledge_query"] == "jakie pola i opcje są dostępne w /converter?"


@pytest.mark.asyncio
async def test_knowledge_query_does_not_accept_same_value_candidate() -> None:
    message = "jakie opcje converter dostepne?"
    candidate = MutationCandidate(
        action=CandidateAction.SET,
        path="/converter/outputFilename",
        value="sap_{{data_danych}}.csv",
        confidence=0.92,
        evidence=message,
    )
    orchestrator, sessions, audit_sink = build_orchestrator(
        {
            message: IntentResolution(
                intent_kind=IntentKind.KNOWLEDGE,
                candidates=[candidate],
                knowledge_query="jakie pola i opcje są dostępne w /converter?",
            )
        }
    )
    await seed_session(sessions, sample_document())
    before = await sessions.get("session-1")
    assert before is not None
    document_before = deepcopy(before.contract.document)
    provenance_before = deepcopy(before.contract.provenance)
    revision_before = before.contract.revision
    mutation_log_before = deepcopy(before.contract.mutation_log)

    await orchestrator.run_turn("session-1", message)

    after = await sessions.get("session-1")
    assert after is not None
    assert after.contract.document == document_before
    assert after.contract.provenance == provenance_before
    assert after.contract.revision == revision_before
    assert after.contract.mutation_log == mutation_log_before
    assert not [event for event in audit_sink.events if event.event_type == "candidate.accepted"]
    intent_event = next(event for event in audit_sink.events if event.event_type == "intent.resolved")
    assert intent_event.data["intent_kind"] == "knowledge"
    assert intent_event.data["candidates"][0]["path"] == "/converter/outputFilename"


class SpyCandidatePolicy(CandidatePolicy):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def evaluate(
        self,
        state: ContractState,
        candidates: list[MutationCandidate],
    ) -> CandidatePolicyResult:
        self.calls += 1
        return super().evaluate(state, candidates)


@pytest.mark.asyncio
async def test_unresolved_skips_candidate_policy_and_composes_clarification() -> None:
    message = "niejasna wypowiedź"
    spy = SpyCandidatePolicy()
    candidate = MutationCandidate(
        action=CandidateAction.SET,
        path="/converter/outputFilename",
        value="should-not-apply.csv",
        confidence=0.99,
        evidence=message,
    )
    orchestrator, sessions, audit_sink = build_orchestrator(
        {
            message: IntentResolution(
                intent_kind=IntentKind.UNRESOLVED,
                candidates=[candidate],
                unresolved=[{"value": message, "reason": "ambiguous"}],
            )
        },
        candidate_policy=spy,
    )
    await seed_session(sessions, sample_document())

    outcome = await orchestrator.run_turn("session-1", message)

    assert spy.calls == 0
    assert outcome.intent_kind is IntentKind.UNRESOLVED
    assert outcome.message.startswith("Nie udało mi się jednoznacznie zrozumieć")
    assert "YAML:" not in outcome.message
    assert "valid=" not in outcome.message
    assert not outcome.new_events
    assert not any(event.event_type == "candidate.accepted" for event in audit_sink.events)

    composed = await BasicResponseComposer().compose(outcome)
    assert composed.startswith("Nie udało mi się jednoznacznie zrozumieć")
    assert "YAML:" not in composed
    assert "valid=" not in composed


@pytest.mark.asyncio
async def test_malformed_knowledge_degrades_to_unresolved_end_to_end() -> None:
    message = "jakie opcje?"
    spy = SpyCandidatePolicy()
    candidate = MutationCandidate(
        action=CandidateAction.SET,
        path="/converter/outputFilename",
        value="should-not-apply.csv",
        confidence=0.99,
        evidence=message,
    )
    orchestrator, sessions, audit_sink = build_orchestrator(
        {
            message: IntentResolution(
                intent_kind=IntentKind.KNOWLEDGE,
                candidates=[candidate],
                knowledge_query="  ",
            )
        },
        candidate_policy=spy,
    )
    await seed_session(sessions, sample_document())

    outcome = await orchestrator.run_turn("session-1", message)

    assert spy.calls == 0
    assert outcome.intent_kind is IntentKind.UNRESOLVED
    assert outcome.message.startswith("Nie udało mi się jednoznacznie zrozumieć")
    assert outcome.unresolved == [
        {"reason": "knowledge_query is required for this intent kind"}
    ]
    assert not outcome.new_events
    assert not any(event.event_type == "candidate.accepted" for event in audit_sink.events)

    intent_event = next(
        event for event in audit_sink.events if event.event_type == "intent.resolved"
    )
    assert intent_event.data["intent_kind"] == "knowledge"
    assert intent_event.data["knowledge_query"] == "  "
    assert intent_event.data["candidates"][0]["path"] == "/converter/outputFilename"

    deferred = [
        event.data
        for event in audit_sink.events
        if event.event_type == "candidate.deferred"
    ]
    assert deferred == [
        {"reason": "knowledge_query is required for this intent kind"}
    ]
