from copy import deepcopy

import pytest

from adcm.orchestrator import ADCMOrchestrator
from support import FakeForgeGateway


def build_service():
    return ADCMOrchestrator(FakeForgeGateway())


@pytest.mark.asyncio
async def test_guided_loop_minimal():
    service = build_service()
    turn = await service.start()
    assert turn.pending_path == "metadata.sourceSystemGcpId"

    turn = await service.message(turn.session_id, "roket")
    assert turn.pending_path == "metadata.id"

    turn = await service.message(turn.session_id, "customer_accounts_daily")
    assert turn.pending_path == "metadata.owner"

    turn = await service.message(turn.session_id, "data-platform@example.com")
    assert turn.pending_path == "source.uri"

    turn = await service.message(turn.session_id, "gs://raw-zone/accounts/accounts.dat")
    assert turn.pending_path == "source.columns"

    turn = await service.message(
        turn.session_id,
        "account_id 0 8 STRING NOT NULL\nbalance 8 20 NUMERIC",
    )
    assert turn.status == "complete"
    assert turn.contract["metadata"]["sourceSystemGcpId"] == "ROCKET"

class FakeSemanticResolver:
    def __init__(self, answers):
        self.answers = answers
        self.calls = []

    async def extract_from_history(self, session_id, messages, requirements, contract):
        self.calls.append([r.path for r in requirements])
        return {
            r.path: self.answers[r.path]
            for r in requirements
            if r.path in self.answers
        }


class RecordingFakeForgeGateway(FakeForgeGateway):
    def __init__(self):
        super().__init__()
        self.submissions = []

    async def submit_values(self, session_id, values, origin):
        self.submissions.append(deepcopy(values))
        return await super().submit_values(session_id, values, origin)


@pytest.mark.asyncio
async def test_explicit_source_gate_never_calls_semantic_resolver():
    semantic = FakeSemanticResolver({"metadata.sourceSystemGcpId": "rocket"})
    service = ADCMOrchestrator(FakeForgeGateway(), semantic=semantic)
    turn = await service.start()

    turn = await service.message(turn.session_id, "wybierz za mnie")

    assert turn.pending_path == "metadata.sourceSystemGcpId"
    assert semantic.calls == []


@pytest.mark.asyncio
async def test_stair_step_loop_reuses_information_as_forge_reveals_requirements():
    semantic = FakeSemanticResolver({
        "metadata.id": "customer_accounts_daily",
        "metadata.owner": "data-platform@example.com",
        "source.uri": "gs://raw-zone/accounts/accounts.dat",
        "source.columns": [
            {"name": "account_id", "start": 0, "end": 8, "dataType": "STRING", "nullable": False},
            {"name": "balance", "start": 8, "end": 20, "dataType": "NUMERIC"},
        ],
    })
    service = ADCMOrchestrator(FakeForgeGateway(), semantic=semantic)
    turn = await service.start()

    # The user states everything up-front, but the explicit metadata.id gate cannot
    # be completed by the semantic resolver.
    turn = await service.message(
        turn.session_id,
        "Rocket. Chcę utworzyć customer accounts daily, owner data-platform, "
        "plik mam w raw zone i wkleiłem też definicję kolumn.",
    )

    assert turn.pending_path == "metadata.id"
    assert semantic.calls == []

    turn = await service.message(turn.session_id, "pipeline: customer_accounts_daily")

    assert turn.status == "complete"
    assert semantic.calls
    assert all("metadata.sourceSystemGcpId" not in call for call in semantic.calls)
    assert all("metadata.id" not in call for call in semantic.calls)
    assert turn.contract["metadata"]["id"] == "customer_accounts_daily"
    assert turn.contract["source"]["uri"].startswith("gs://")


@pytest.mark.asyncio
async def test_baseline_stair_step_and_adcm_conversation_state_ownership():
    gateway = RecordingFakeForgeGateway()
    semantic = FakeSemanticResolver({
        "source.columns": [
            {"name": "account_id", "start": 0, "end": 8, "dataType": "STRING", "nullable": False},
        ],
    })
    service = ADCMOrchestrator(gateway, semantic=semantic)

    turn = await service.start()
    assert turn.pending_path == "metadata.sourceSystemGcpId"

    turn = await service.message(
        turn.session_id,
        "Rocket; plik gs://raw-zone/accounts/accounts.dat; mam definicje kolumn; "
        "owner: data-platform@example.com",
    )
    assert turn.pending_path == "metadata.id"

    turn = await service.message(turn.session_id, "pipeline: customer_accounts_daily")

    # Direct source-system and metadata.id submits are interleaved with two automatic
    # history-driven steps: deterministic owner/URI extraction and semantic columns.
    assert [set(submission) for submission in gateway.submissions] == [
        {"metadata.sourceSystemGcpId"},
        {"metadata.owner", "source.uri"},
        {"metadata.id"},
        {"source.columns"},
    ]
    assert turn.status == "complete"

    memory = service.sessions[turn.session_id]
    assert [message.role for message in memory.messages] == [
        "assistant",
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert "contract" not in type(memory).model_fields
    assert not hasattr(gateway, "messages")
