from copy import deepcopy

import pytest

from adcm.models import ConversationMemory, ExtractionMethod, Origin, Requirement
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
        self.calls.append([requirement.path for requirement in requirements])
        return {
            requirement.path: self.answers[requirement.path]
            for requirement in requirements
            if requirement.path in self.answers
        }


class RecordingFakeForgeGateway(FakeForgeGateway):
    def __init__(self):
        super().__init__()
        self.submissions = []
        self.submission_origins = []

    async def submit_values(self, session_id, values, origin):
        self.submissions.append(deepcopy(values))
        self.submission_origins.append(origin)
        return await super().submit_values(session_id, values, origin)


class RejectingFakeForgeGateway(RecordingFakeForgeGateway):
    async def submit_values(self, session_id, values, origin):
        self._check_session(session_id)
        self.submissions.append(deepcopy(values))
        self.submission_origins.append(origin)
        return self._state()


async def advance_to_csv_columns(service: ADCMOrchestrator):
    turn = await service.start()
    turn = await service.message(turn.session_id, "sap")
    turn = await service.message(turn.session_id, "pipeline: customer_daily")
    turn = await service.message(turn.session_id, "data-platform@example.com")
    turn = await service.message(turn.session_id, "gs://raw-zone/customer.csv")
    assert turn.pending_path == "source.columns"
    return turn


@pytest.mark.asyncio
async def test_explicit_source_gate_never_calls_semantic_resolver():
    semantic = FakeSemanticResolver({"metadata.sourceSystemGcpId": "rocket"})
    service = ADCMOrchestrator(FakeForgeGateway(), semantic=semantic)
    turn = await service.start()

    turn = await service.message(turn.session_id, "wybierz za mnie")

    assert turn.pending_path == "metadata.sourceSystemGcpId"
    assert semantic.calls == []


@pytest.mark.asyncio
async def test_t1_stair_step_resolves_information_given_up_front():
    gateway = RecordingFakeForgeGateway()
    semantic = FakeSemanticResolver(
        {
            "source.columns": [
                {"name": "should_not_be_used", "dataType": "STRING"},
            ],
        }
    )
    service = ADCMOrchestrator(gateway, semantic=semantic)
    turn = await service.start()

    turn = await service.message(
        turn.session_id,
        "Rocket. pipeline: customer_accounts_daily; owner: data-platform@example.com; "
        "uri: gs://raw-zone/accounts/accounts.dat",
    )

    assert turn.pending_path == "source.columns"
    assert semantic.calls == []
    assert gateway.submissions == [
        {"metadata.sourceSystemGcpId": "rocket"},
        {"metadata.id": "customer_accounts_daily"},
        {"metadata.owner": "data-platform@example.com"},
        {"source.uri": "gs://raw-zone/accounts/accounts.dat"},
    ]


@pytest.mark.asyncio
async def test_t2_latest_user_fact_wins_when_requirement_appears():
    gateway = RecordingFakeForgeGateway()
    service = ADCMOrchestrator(gateway)
    turn = await service.start()

    turn = await service.message(turn.session_id, "owner: team_a")
    turn = await service.message(turn.session_id, "owner: team_b")
    turn = await service.message(turn.session_id, "rocket")

    owner_fact = service.sessions[turn.session_id].get_fact("metadata.owner")
    assert gateway.contract["metadata"]["owner"] == "team_b"
    assert owner_fact is not None
    assert owner_fact.value == "team_b"
    assert owner_fact.message_sequence == 2
    assert {"metadata.owner": "team_b"} in gateway.submissions


@pytest.mark.asyncio
async def test_t3_user_fact_overrides_system_enrichment_when_not_pending():
    gateway = RecordingFakeForgeGateway()
    service = ADCMOrchestrator(gateway)
    turn = await service.start()

    turn = await service.message(turn.session_id, "0 6 * * *")
    turn = await service.message(turn.session_id, "rocket")

    assert turn.pending_path == "metadata.id"
    assert gateway.contract["orchestration"]["schedule"] == "0 6 * * *"
    assert gateway.origins["orchestration.schedule"] == Origin.USER
    assert {"orchestration.schedule": "0 6 * * *"} in gateway.submissions


@pytest.mark.asyncio
async def test_t4_missing_information_returns_one_precise_question_without_llm():
    semantic = FakeSemanticResolver({"metadata.sourceSystemGcpId": "rocket"})
    service = ADCMOrchestrator(FakeForgeGateway(), semantic=semantic)
    turn = await service.start()

    turn = await service.message(turn.session_id, "nie wiem")

    assert turn.pending_path == "metadata.sourceSystemGcpId"
    assert turn.message == "Jaki jest system źródłowy? Dostępne: rocket, sap."
    assert semantic.calls == []


@pytest.mark.asyncio
async def test_t5_rejected_candidate_stops_without_looping_and_explains_failure():
    gateway = RejectingFakeForgeGateway()
    service = ADCMOrchestrator(gateway)
    turn = await service.start()

    turn = await service.message(turn.session_id, "rocket")

    assert gateway.submissions == [{"metadata.sourceSystemGcpId": "rocket"}]
    assert turn.pending_path == "metadata.sourceSystemGcpId"
    assert turn.candidate_issues[0]["validator"] == "no_progress"
    assert "nie zastosował kandydata" in turn.message


@pytest.mark.asyncio
async def test_stage04_t1_names_only_are_stored_as_partial_without_forge_submit():
    gateway = RecordingFakeForgeGateway()
    service = ADCMOrchestrator(gateway)
    turn = await advance_to_csv_columns(service)
    submissions_before = len(gateway.submissions)

    turn = await service.message(turn.session_id, "data_d, sap1,sap2,sap3")

    memory = service.sessions[turn.session_id]
    partial = memory.get_partial("source.columns")
    assert len(gateway.submissions) == submissions_before
    assert memory.get_fact("source.columns") is None
    assert partial is not None
    assert partial.value == [
        {"name": "data_d"},
        {"name": "sap1"},
        {"name": "sap2"},
        {"name": "sap3"},
    ]
    assert partial.missing == ["dataType"]
    assert "Rozpoznałem 4 elementy" in turn.message
    assert "dataType dla: data_d, sap1, sap2, sap3" in turn.message


@pytest.mark.asyncio
async def test_stage04_t2_follow_up_types_merge_and_submit_complete_candidate():
    gateway = RecordingFakeForgeGateway()
    service = ADCMOrchestrator(gateway)
    turn = await advance_to_csv_columns(service)
    turn = await service.message(turn.session_id, "data_d\nsap1\nsap2\nsap3")

    turn = await service.message(
        turn.session_id,
        "data_d date\nsap1 string\nsap2 STRING\nsap3 numeric",
    )

    assert turn.status == "complete"
    assert gateway.submissions[-1] == {
        "source.columns": [
            {"name": "data_d", "dataType": "DATE"},
            {"name": "sap1", "dataType": "STRING"},
            {"name": "sap2", "dataType": "STRING"},
            {"name": "sap3", "dataType": "NUMERIC"},
        ]
    }
    assert service.sessions[turn.session_id].get_partial("source.columns") is None


@pytest.mark.asyncio
async def test_stage04_t4_invalid_datatype_gets_narrow_clarification():
    gateway = RecordingFakeForgeGateway()
    service = ADCMOrchestrator(gateway)
    turn = await advance_to_csv_columns(service)
    submissions_before = len(gateway.submissions)

    turn = await service.message(turn.session_id, "data_d ORACLE_NUMBER")

    partial = service.sessions[turn.session_id].get_partial("source.columns")
    assert len(gateway.submissions) == submissions_before
    assert partial is not None
    assert partial.value == [{"name": "data_d"}]
    assert partial.invalid == ["data_d.dataType=ORACLE_NUMBER"]
    assert "Nie rozpoznałem wartości: data_d.dataType=ORACLE_NUMBER" in turn.message
    assert "Dozwolone wartości" in turn.message


def test_stage04_structured_input_binds_only_to_first_compatible_requirement():
    service = build_service()
    memory = ConversationMemory(
        session_id="adcm-session",
        forge_session_id="forge-session",
    )
    message = memory.add_user_message("account_id STRING")
    value_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["name", "dataType"],
            "properties": {
                "name": {"type": "string"},
                "dataType": {"type": "string", "enum": ["STRING", "DATE"]},
            },
        },
    }
    source = Requirement(
        path="source.fields",
        question="source fields",
        value_schema=value_schema,
    )
    derived_target = Requirement(
        path="derived.target.fields",
        question="target fields",
        value_schema=value_schema,
    )
    values = {}

    service._merge_current_structured(
        memory,
        message,
        message.content,
        [source, derived_target],
        source.path,
        values,
    )

    assert values == {
        "source.fields": [{"name": "account_id", "dataType": "STRING"}]
    }
    assert memory.get_partial("derived.target.fields") is None


@pytest.mark.asyncio
async def test_baseline_stair_step_and_adcm_conversation_state_ownership():
    gateway = RecordingFakeForgeGateway()
    semantic = FakeSemanticResolver(
        {
            "source.columns": [
                {"name": "account_id", "dataType": "STRING"},
            ],
        }
    )
    service = ADCMOrchestrator(gateway, semantic=semantic)

    turn = await service.start()
    turn = await service.message(
        turn.session_id,
        "Rocket; plik gs://raw-zone/accounts/accounts.dat; owner: data-platform@example.com",
    )
    turn = await service.message(turn.session_id, "pipeline: customer_accounts_daily")

    assert [set(submission) for submission in gateway.submissions] == [
        {"metadata.sourceSystemGcpId"},
        {"metadata.owner"},
        {"source.uri"},
        {"metadata.id"},
    ]
    assert gateway.submission_origins == [Origin.USER] * 4
    assert turn.pending_path == "source.columns"
    assert semantic.calls == []

    memory = service.sessions[turn.session_id]
    assert [message.role for message in memory.messages] == [
        "assistant",
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert memory.get_fact("source.columns") is None
    assert "contract" not in type(memory).model_fields
    assert not hasattr(gateway, "messages")


@pytest.mark.asyncio
async def test_deterministic_extraction_records_sequenced_user_facts():
    service = build_service()
    turn = await service.start()

    turn = await service.message(turn.session_id, "roket")
    turn = await service.message(turn.session_id, "pipeline: customer_accounts_daily")

    memory = service.sessions[turn.session_id]
    source_fact = memory.get_fact("metadata.sourceSystemGcpId")
    pipeline_fact = memory.get_fact("metadata.id")

    assert source_fact.value == "rocket"
    assert source_fact.message_sequence == 1
    assert source_fact.extraction_method == ExtractionMethod.DETERMINISTIC
    assert source_fact.evidence == "roket"
    assert pipeline_fact.value == "customer_accounts_daily"
    assert pipeline_fact.message_sequence == 2
    assert [
        message.message_sequence
        for message in memory.messages
        if message.role == "user"
    ] == [1, 2]
