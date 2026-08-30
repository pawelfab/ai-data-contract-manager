import pytest

from adcm.adapters.response_basic import BasicResponseComposer
from adcm.adapters.session_memory import InMemorySessionRepository
from adcm.application.candidate_policy import CandidatePolicy
from adcm.application.document_engine import DocumentEngine
from adcm.application.external_check_coordinator import ExternalCheckCoordinator
from adcm.application.observability.app_log_recorder import AppLogRecorder
from adcm.application.observability.session_audit_recorder import SessionAuditRecorder
from adcm.application.proposal_reconciler import ProposalReconciler
from adcm.application.rules_engine import ConventionRulesEngine
from adcm.application.stabilization_engine import StabilizationEngine
from adcm.application.turn_orchestrator import TurnOrchestrator
from adcm.domain.forge import ContractStatus, ForgeAnalysis, ForgeDescription
from adcm.domain.mutations import CandidateAction, MutationCandidate
from adcm.domain.rules import ConventionRule, RulesDocument
from adcm.domain.turn import IntentKind, IntentResolution


class CaptureSink:
    def __init__(self) -> None:
        self.events = []

    def emit(self, event) -> None:
        self.events.append(event)


class FakeForge:
    def __init__(self) -> None:
        self.correlations: list[tuple[str, str | None]] = []

    async def describe(self, *, correlation_id: str | None = None) -> ForgeDescription:
        self.correlations.append(("describe", correlation_id))
        return ForgeDescription(protocol_version="1.0", definition_version="fake")

    async def analyze(self, document: dict, *, correlation_id: str | None = None) -> ForgeAnalysis:
        self.correlations.append(("analyze", correlation_id))
        return ForgeAnalysis(
            protocol_version="1.0",
            definition_version="fake",
            status=ContractStatus(valid=True, complete=True, clean=True),
        )


class FakeIntent:
    async def resolve(self, message: str, *, document: dict, definition=None) -> IntentResolution:
        return IntentResolution(
            intent_kind=IntentKind.MUTATION,
            candidates=[
                MutationCandidate(
                    action=CandidateAction.SET,
                    path="/metadata/sourceSystemGcpId",
                    value="sap",
                    confidence=0.99,
                    evidence=message,
                )
            ],
            unresolved=[{"value": "separator=;", "reason": "source type is not known"}],
        )


class RulesRepository:
    def __init__(self, rules: list[ConventionRule] | None = None) -> None:
        self.rules = rules or []

    async def load(self, session_id: str) -> RulesDocument:
        return RulesDocument(version="test", rules=self.rules)


def build_orchestrator(audit_sink, *, rules: list[ConventionRule] | None = None):
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
    orchestrator = TurnOrchestrator(
        sessions=InMemorySessionRepository(),
        forge=forge,
        intent=FakeIntent(),
        rules=RulesRepository(rules),
        response=BasicResponseComposer(),
        candidate_policy=CandidatePolicy(),
        document_engine=document_engine,
        stabilization=stabilization,
        external_checks=ExternalCheckCoordinator(),
        audit=audit,
        app_log=app_log,
    )
    return orchestrator, forge, app_sink


@pytest.mark.asyncio
async def test_turn_audit_preserves_order_raw_intent_decisions_and_snapshot() -> None:
    audit_sink = CaptureSink()
    rule = ConventionRule(
        id="system.override",
        path="/metadata/sourceSystemGcpId",
        value="rocket",
    )
    orchestrator, forge, _ = build_orchestrator(audit_sink, rules=[rule])

    outcome = await orchestrator.run_turn("aaa", "system sap", correlation_id="corr-1")

    event_types = [event.event_type for event in audit_sink.events]
    ordered = [
        "turn.started",
        "user.message.received",
        "intent.resolved",
        "candidate.accepted",
        "candidate.deferred",
        "mutation.applied",
        "stabilization.round.started",
        "forge.analysis.started",
        "forge.analysis.completed",
        "rule.proposal.generated",
        "proposal.decision",
        "stabilization.round.completed",
        "stabilization.completed",
        "external_checks.completed",
        "response.composed",
        "turn.completed",
    ]
    positions = [event_types.index(event_type) for event_type in ordered]
    assert positions == sorted(positions)

    intent_event = next(event for event in audit_sink.events if event.event_type == "intent.resolved")
    assert intent_event.data["candidates"][0]["path"] == "/metadata/sourceSystemGcpId"
    assert intent_event.data["candidates"][0]["value"] == "sap"

    decisions = [event for event in audit_sink.events if event.event_type == "proposal.decision"]
    assert decisions[0].data["proposal_id"] == "rule:system.override"
    assert decisions[0].data["current_source"] == "user_explicit"
    assert decisions[0].data["proposed_value"] == "rocket"

    mutations = [event for event in audit_sink.events if event.event_type == "mutation.applied"]
    assert len([event for event in mutations if event.data["path"] == "/metadata/sourceSystemGcpId"]) == 1
    completed = next(event for event in audit_sink.events if event.event_type == "turn.completed")
    assert completed.data["final_document"] == outcome.document
    assert completed.data["response"] == outcome.message
    assert {correlation for _, correlation in forge.correlations} == {"corr-1"}
    assert {event.correlation_id for event in audit_sink.events} == {"corr-1"}


@pytest.mark.asyncio
async def test_audit_sink_failure_does_not_fail_turn_and_creates_app_error() -> None:
    class BrokenAuditSink:
        def emit(self, event) -> None:
            raise RuntimeError("audit unavailable")

    orchestrator, _, app_sink = build_orchestrator(BrokenAuditSink())

    outcome = await orchestrator.run_turn("aaa", "system sap", correlation_id="corr-failure")

    assert outcome.document["metadata"]["sourceSystemGcpId"] == "sap"
    failures = [event for event in app_sink.events if event.event == "session_audit_sink_failed"]
    assert failures
    assert failures[0].level == "ERROR"
    assert failures[0].correlation_id == "corr-failure"
    assert failures[0].data["failed_event_type"] == "turn.started"
