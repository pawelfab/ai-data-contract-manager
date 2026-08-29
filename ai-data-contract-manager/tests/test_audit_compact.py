import json

import pytest

from adcm.adapters.logging.local_session_audit_sink import LocalSessionAuditSink
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
from adcm.domain.forge import (
    ContractStatus,
    ForgeAnalysis,
    ForgeDescription,
    ForgeProposal,
    MissingRequirement,
    WritableTarget,
)
from adcm.domain.mutations import CandidateAction, MutationCandidate
from adcm.domain.rules import ConventionRule, RuleCondition, RulesDocument
from adcm.domain.turn import IntentResolution

# A writable list large enough to dominate the payload when it is repeated per round,
# which is exactly what the compact audit must avoid.
WRITABLE = [
    WritableTarget(
        path=f"/metadata/field{index}",
        value_type="string",
        title=f"Field {index}",
        description=f"Description of field {index} as returned by the contract definition.",
    )
    for index in range(15)
]

MISSING = [
    MissingRequirement(
        path="/metadata/dataFileId",
        message="Required value missing at /metadata/dataFileId",
        expected_type="string",
    ),
    MissingRequirement(
        path="/source/sourceType",
        message="Required value missing at /source/sourceType",
        expected_type="string",
        allowed_values=["csv", "txt", "json", "jdbc", "fixed_width"],
    ),
]

# One proposal per analysis, so the fixed point needs several rounds to settle.
ROUND_PROPOSALS = [
    ForgeProposal(
        id="default:/metadata/version",
        path="/metadata/version",
        value="1.0.0",
        origin="default",
        reason="JSON Schema default",
    ),
    ForgeProposal(
        id="default:/metadata/owner",
        path="/metadata/owner",
        value="data-platform",
        origin="default",
        reason="JSON Schema default",
    ),
]

DERIVE_METADATA_ID = ConventionRule(
    id="global.source_system.metadata_id",
    path="/metadata/id",
    value="{/metadata/sourceSystemGcpId}",
    when=RuleCondition(path="/metadata/id", exists=False),
)


class CaptureSink:
    def __init__(self) -> None:
        self.events = []

    def emit(self, event) -> None:
        self.events.append(event)


class MultiRoundForge:
    def __init__(self) -> None:
        self.analyze_calls = 0

    async def describe(self, *, correlation_id: str | None = None) -> ForgeDescription:
        return ForgeDescription(protocol_version="1.0", definition_version="baseline-1")

    async def analyze(self, document: dict, *, correlation_id: str | None = None) -> ForgeAnalysis:
        proposals = (
            [ROUND_PROPOSALS[self.analyze_calls]] if self.analyze_calls < len(ROUND_PROPOSALS) else []
        )
        self.analyze_calls += 1
        return ForgeAnalysis(
            protocol_version="1.0",
            definition_version="baseline-1",
            writable=WRITABLE,
            missing=MISSING,
            proposals=proposals,
            status=ContractStatus(valid=True, complete=False, clean=True),
        )


class FakeIntent:
    async def resolve(self, message: str, *, document: dict, definition=None) -> IntentResolution:
        return IntentResolution(
            candidates=[
                MutationCandidate(
                    action=CandidateAction.SET,
                    path="/metadata/sourceSystemGcpId",
                    value="sap",
                    confidence=0.99,
                    evidence=message,
                )
            ],
            knowledge_query=None,
            unresolved=[{"value": "separator=;", "reason": "source type is not known"}],
        )


class RulesRepository:
    def __init__(self, rules: list[ConventionRule]) -> None:
        self.rules = rules

    async def load(self, session_id: str) -> RulesDocument:
        return RulesDocument(version="test", rules=self.rules)


def build_orchestrator(audit_sink, *, level: str = "normal"):
    app_log = AppLogRecorder(CaptureSink(), environment="test")
    forge = MultiRoundForge()
    document_engine = DocumentEngine()
    return TurnOrchestrator(
        sessions=InMemorySessionRepository(),
        forge=forge,
        intent=FakeIntent(),
        rules=RulesRepository([DERIVE_METADATA_ID]),
        response=BasicResponseComposer(),
        candidate_policy=CandidatePolicy(),
        document_engine=document_engine,
        stabilization=StabilizationEngine(
            forge,
            document_engine,
            ConventionRulesEngine(),
            ProposalReconciler(),
        ),
        external_checks=ExternalCheckCoordinator(),
        audit=SessionAuditRecorder(audit_sink, app_log, level=level),
        app_log=app_log,
    )


async def run_multi_round_turn(audit_sink, *, level: str = "normal", session_id: str = "compact"):
    orchestrator = build_orchestrator(audit_sink, level=level)
    return await orchestrator.run_turn(session_id, "system sap", correlation_id="corr-compact")


def events_of(sink, event_type: str):
    return [event for event in sink.events if event.event_type == event_type]


@pytest.mark.asyncio
async def test_forge_analysis_completed_is_compact_summary_in_normal_mode() -> None:
    sink = CaptureSink()
    await run_multi_round_turn(sink)

    analyses = events_of(sink, "forge.analysis.completed")
    assert len(analyses) >= 2
    for event in analyses:
        data = event.data
        assert data["status"] == {"valid": True, "complete": False, "clean": True}
        assert data["writable_count"] == len(WRITABLE)
        assert data["missing"] == ["/metadata/dataFileId", "/source/sourceType"]
        assert data["foreign_count"] == 0
        assert data["diagnostic_count"] == 0
        assert isinstance(data["proposal_count"], int)
        assert isinstance(data["duration_ms"], float)
        assert isinstance(data["round"], int)
        assert isinstance(data["contract_revision"], int)
        assert data["definition_version"] == "baseline-1"
        # The bulky per-round repetitions are gone.
        assert "writable" not in data
        assert "proposals" not in data
        assert "foreign" not in data
        # No empty structure when there is nothing to report.
        assert "diagnostics" not in data


@pytest.mark.asyncio
async def test_intent_resolved_keeps_full_candidates() -> None:
    sink = CaptureSink()
    await run_multi_round_turn(sink)

    data = events_of(sink, "intent.resolved")[0].data
    assert set(data) == {"candidates", "knowledge_query", "unresolved"}
    candidate = data["candidates"][0]
    assert candidate["path"] == "/metadata/sourceSystemGcpId"
    assert candidate["value"] == "sap"
    assert candidate["confidence"] == 0.99
    assert candidate["evidence"] == "system sap"
    assert data["unresolved"] == [{"value": "separator=;", "reason": "source type is not known"}]


@pytest.mark.asyncio
async def test_mutation_applied_keeps_values_and_provenance() -> None:
    sink = CaptureSink()
    await run_multi_round_turn(sink)

    mutations = events_of(sink, "mutation.applied")
    assert mutations
    required = {
        "mutation_id",
        "revision_before",
        "revision_after",
        "operation",
        "path",
        "old_exists",
        "old_value",
        "new_exists",
        "new_value",
        "source",
        "producer_id",
        "reason",
    }
    for event in mutations:
        assert required <= set(event.data)

    user_mutation = next(m for m in mutations if m.data["path"] == "/metadata/sourceSystemGcpId")
    assert user_mutation.data["old_exists"] is False
    assert user_mutation.data["new_value"] == "sap"
    assert user_mutation.data["source"] == "user_explicit"


@pytest.mark.asyncio
async def test_turn_completed_is_final_snapshot_without_proposal_history() -> None:
    sink = CaptureSink()
    outcome = await run_multi_round_turn(sink)

    data = events_of(sink, "turn.completed")[0].data
    assert data["final_document"] == outcome.document
    assert data["forge_status"] == {"valid": True, "complete": False, "clean": True}
    assert data["response"] == outcome.message
    assert data["missing"] == [
        {"path": "/metadata/dataFileId", "code": "required", "expected_type": "string"},
        {
            "path": "/source/sourceType",
            "code": "required",
            "expected_type": "string",
            "allowed_values": ["csv", "txt", "json", "jdbc", "fixed_width"],
        },
    ]
    assert data["diagnostics"] == []
    assert set(data["external_checks"]) == {"performed", "skipped", "failed", "degraded"}
    # The whole proposal history stays in the dedicated events, not here.
    assert data["stabilization"] == {
        "rounds": outcome.stabilization.rounds,
        "converged": outcome.stabilization.converged,
    }
    assert "proposal_decisions" not in data["stabilization"]


@pytest.mark.asyncio
async def test_proposal_decision_and_mutation_chain_is_reconstructable() -> None:
    sink = CaptureSink()
    await run_multi_round_turn(sink)

    proposal_ids = {
        event.data["id"]
        for event in sink.events
        if event.event_type in {"forge.proposal.received", "rule.proposal.generated"}
    }
    decisions = events_of(sink, "proposal.decision")
    assert decisions
    linked = [d for d in decisions if d.data["proposal_id"] is not None]
    assert linked
    for decision in linked:
        # Every decision joins back to the event that emitted its proposal.
        assert decision.data["proposal_id"] in proposal_ids
    for decision in decisions:
        assert decision.data["reason"]

    mutated_paths = {event.data["path"] for event in events_of(sink, "mutation.applied")}
    applied_paths = {d.data["path"] for d in decisions if d.data["action"] == "apply"}
    assert applied_paths
    assert applied_paths <= mutated_paths

    # Every applied proposal is emitted before the decision that consumed it.
    order = [event.event_type for event in sink.events]
    assert order.index("forge.proposal.received") < order.index("proposal.decision")


@pytest.mark.asyncio
async def test_multi_round_stabilization_stays_readable() -> None:
    sink = CaptureSink()
    outcome = await run_multi_round_turn(sink)

    started = events_of(sink, "stabilization.round.started")
    completed = events_of(sink, "stabilization.round.completed")
    assert len(started) >= 2
    assert len(started) == len(completed)
    assert [event.data["round"] for event in completed] == list(range(1, len(completed) + 1))
    assert completed[0].data["changed"] is True
    assert completed[-1].data["changed"] is False
    for start, end in zip(started, completed):
        assert start.data["contract_revision"] == end.data["revision_before"]
        assert end.data["revision_after"] >= end.data["revision_before"]

    final = events_of(sink, "stabilization.completed")[0].data
    assert final == {
        "rounds": outcome.stabilization.rounds,
        "converged": True,
        "final_revision": completed[-1].data["revision_after"],
    }


@pytest.mark.asyncio
async def test_event_envelope_is_unchanged() -> None:
    sink = CaptureSink()
    await run_multi_round_turn(sink, session_id="envelope")

    assert sink.events
    for event in sink.events:
        assert event.session_id == "envelope"
        assert event.turn_no == 1
        assert event.correlation_id == "corr-compact"
        assert event.event_id is not None
        assert event.timestamp is not None
        assert event.event_type


@pytest.mark.asyncio
async def test_debug_level_keeps_full_forge_analysis() -> None:
    sink = CaptureSink()
    await run_multi_round_turn(sink, level="debug")

    data = events_of(sink, "forge.analysis.completed")[0].data
    assert len(data["writable"]) == len(WRITABLE)
    assert data["missing"][0]["message"] == "Required value missing at /metadata/dataFileId"
    assert "proposals" in data
    assert "round" in data and "contract_revision" in data and "duration_ms" in data


@pytest.mark.asyncio
async def test_compact_audit_is_substantially_smaller_than_full_audit(tmp_path, capsys) -> None:
    for level, session_id in (("debug", "size-debug"), ("normal", "size-normal")):
        await run_multi_round_turn(
            LocalSessionAuditSink(tmp_path), level=level, session_id=session_id
        )

    before = (tmp_path / "sessions" / "size-debug.jsonl").read_bytes()
    after = (tmp_path / "sessions" / "size-normal.jsonl").read_bytes()

    # Same turn, same event stream — only the payloads differ.
    assert before.count(b"\n") == after.count(b"\n")

    def payload_bytes(raw: bytes) -> int:
        return sum(
            len(json.dumps(json.loads(line)["data"], ensure_ascii=False).encode("utf-8"))
            for line in raw.splitlines()
        )

    with capsys.disabled():
        print(
            f"\nsession audit size: {len(before)} B -> {len(after)} B "
            f"({100 * (len(before) - len(after)) / len(before):.1f}% smaller), "
            f"payload only: {payload_bytes(before)} B -> {payload_bytes(after)} B"
        )

    assert len(after) < 0.7 * len(before)
