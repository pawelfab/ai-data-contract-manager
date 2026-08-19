import logging
from copy import deepcopy

import pytest

from adcm.models import (
    ConversationMemory,
    ExtractionMethod,
    Origin,
    Requirement,
    UserFact,
)
from adcm.orchestrator import ADCMOrchestrator
from adcm.semantic import CandidateValue, ExtractionResult
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
    def __init__(self, results=()):
        self.results = list(results)
        self.calls = []

    async def extract_from_history(
        self,
        session_id,
        messages,
        pending,
        overridable,
        user_facts,
    ):
        self.calls.append(
            {
                "pending": [requirement.path for requirement in pending],
                "overridable": [requirement.path for requirement in overridable],
                "facts": deepcopy(user_facts),
            }
        )
        if self.results:
            return self.results.pop(0)
        return ExtractionResult()


class RecordingFakeForgeGateway(FakeForgeGateway):
    def __init__(self):
        super().__init__()
        self.submissions = []
        self.submission_origins = []

    async def submit_values(self, session_id, values, origin):
        self.submissions.append(deepcopy(values))
        self.submission_origins.append(origin)
        return await super().submit_values(session_id, values, origin)


class SchemaDrivenFakeForgeGateway(RecordingFakeForgeGateway):
    def __init__(self, requirements: list[Requirement]):
        super().__init__()
        self.extra_requirements = requirements
        self.source_system = "rocket"
        self._set("metadata.sourceSystemGcpId", "ROCKET", Origin.USER)
        self._set("metadata.id", "customer_daily", Origin.USER)
        self._set("metadata.owner", "data-platform@example.com", Origin.USER)
        self._set("source.sourceType", "fixed_width", Origin.SYSTEM_ENRICHMENT)
        self._set("source.uri", "gs://raw-zone/accounts.dat", Origin.USER)
        self._set(
            "source.columns",
            [{"name": "account_id", "start": 0, "end": 8, "dataType": "STRING"}],
            Origin.USER,
        )
        self._set("orchestration.schedule", "0 0 * * *", Origin.USER)

    def _requirements(self) -> list[Requirement]:
        return [
            requirement.model_copy(deep=True)
            for requirement in self.extra_requirements
            if not self._has(requirement.path)
        ]


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


def gateway_with_id_owner_flow(
    *,
    include_id: bool = False,
    include_owner: bool = False,
    schedule_origin: Origin = Origin.USER,
) -> RecordingFakeForgeGateway:
    gateway = RecordingFakeForgeGateway()
    gateway.source_system = "rocket"
    gateway._set("metadata.sourceSystemGcpId", "ROCKET", Origin.USER)
    gateway._set("source.sourceType", "fixed_width", Origin.SYSTEM_ENRICHMENT)
    gateway._set("source.uri", "gs://raw-zone/accounts.dat", Origin.USER)
    gateway._set(
        "source.columns",
        [{"name": "account_id", "start": 0, "end": 8, "dataType": "STRING"}],
        Origin.USER,
    )
    gateway._set("orchestration.schedule", "0 0 * * *", schedule_origin)
    if include_id:
        gateway._set("metadata.id", "customer_daily", Origin.USER)
    if include_owner:
        gateway._set("metadata.owner", "data-platform@example.com", Origin.USER)
    return gateway


@pytest.mark.asyncio
async def test_explicit_source_gate_never_calls_semantic_resolver():
    semantic = FakeSemanticResolver()
    service = ADCMOrchestrator(FakeForgeGateway(), semantic=semantic)
    turn = await service.start()

    turn = await service.message(turn.session_id, "wybierz za mnie")

    assert turn.pending_path == "metadata.sourceSystemGcpId"
    assert semantic.calls == []


@pytest.mark.asyncio
async def test_t1_stair_step_resolves_information_given_up_front():
    gateway = RecordingFakeForgeGateway()
    semantic = FakeSemanticResolver()
    service = ADCMOrchestrator(gateway, semantic=semantic)
    turn = await service.start()

    turn = await service.message(
        turn.session_id,
        "Rocket. pipeline: customer_accounts_daily; owner: data-platform@example.com; "
        "uri: gs://raw-zone/accounts/accounts.dat",
    )

    assert turn.pending_path == "source.columns"
    assert semantic.calls[0]["pending"] == ["source.columns"]
    assert all(
        "metadata.owner" not in call["pending"]
        and "source.uri" not in call["pending"]
        for call in semantic.calls
    )
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
    semantic = FakeSemanticResolver()
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
    semantic = FakeSemanticResolver()
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
    assert semantic.calls[0]["pending"] == ["source.columns"]

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


@pytest.mark.asyncio
async def test_stage05_t1_deterministic_value_skips_llm():
    gateway = gateway_with_id_owner_flow(include_id=True)
    semantic = FakeSemanticResolver()
    service = ADCMOrchestrator(gateway, semantic=semantic)
    turn = await service.start()

    turn = await service.message(turn.session_id, "data-platform@example.com")

    assert turn.status == "complete"
    assert gateway.submissions[-1] == {"metadata.owner": "data-platform@example.com"}
    assert semantic.calls == []


@pytest.mark.asyncio
async def test_stage05_t2_llm_finds_earlier_value_after_deterministic_failure(caplog):
    evidence = "Za opiekę nad tym przepływem odpowiada FinOps."
    gateway = RecordingFakeForgeGateway()
    semantic = FakeSemanticResolver(
        [
            ExtractionResult(
                values=[
                    CandidateValue(
                        path="metadata.owner",
                        value="FinOps",
                        confidence=0.96,
                        evidence=evidence,
                    )
                ]
            )
        ]
    )
    service = ADCMOrchestrator(gateway, semantic=semantic)
    caplog.set_level(logging.DEBUG, logger="adcm.orchestrator")
    turn = await service.start()

    turn = await service.message(turn.session_id, evidence)
    assert turn.pending_path == "metadata.sourceSystemGcpId"
    assert semantic.calls == []

    turn = await service.message(turn.session_id, "rocket")
    assert turn.pending_path == "metadata.id"
    assert semantic.calls == []

    turn = await service.message(turn.session_id, "customer_daily")

    assert turn.pending_path == "source.uri"
    assert {"metadata.owner": "FinOps"} in gateway.submissions
    assert semantic.calls[0]["pending"] == [
        "metadata.owner",
        "source.uri",
        "source.columns",
    ]
    assert semantic.calls[0]["overridable"] == ["orchestration.schedule"]
    assert any(fact.path == "metadata.id" for fact in semantic.calls[0]["facts"])
    assert "method=llm path=metadata.owner confidence=0.960" in caplog.text


@pytest.mark.asyncio
async def test_stage05_t3_illegal_llm_path_is_rejected():
    evidence = "Za opiekę nad tym przepływem odpowiada FinOps."
    gateway = RecordingFakeForgeGateway()
    semantic = FakeSemanticResolver(
        [
            ExtractionResult(
                values=[
                    CandidateValue(
                        path="targets.gold.owner",
                        value="FinOps",
                        confidence=0.99,
                        evidence=evidence,
                    )
                ]
            )
        ]
    )
    service = ADCMOrchestrator(gateway, semantic=semantic)
    turn = await service.start()
    turn = await service.message(turn.session_id, evidence)
    turn = await service.message(turn.session_id, "rocket")

    turn = await service.message(turn.session_id, "customer_daily")

    assert turn.pending_path == "metadata.owner"
    assert all("targets.gold.owner" not in submission for submission in gateway.submissions)
    assert service.sessions[turn.session_id].get_fact("targets.gold.owner") is None


@pytest.mark.asyncio
async def test_stage05_t4_llm_fact_keeps_sequence_and_overrides_enrichment():
    evidence = "Codzienny start ma następować o szóstej rano."
    gateway = RecordingFakeForgeGateway()
    semantic = FakeSemanticResolver(
        [
            ExtractionResult(
                values=[
                    CandidateValue(
                        path="orchestration.schedule",
                        value="0 6 * * *",
                        confidence=0.94,
                        evidence=evidence,
                    )
                ]
            )
        ]
    )
    service = ADCMOrchestrator(gateway, semantic=semantic)
    turn = await service.start()
    turn = await service.message(turn.session_id, evidence)
    turn = await service.message(turn.session_id, "rocket")

    turn = await service.message(turn.session_id, "customer_daily")

    fact = service.sessions[turn.session_id].get_fact("orchestration.schedule")
    assert turn.pending_path == "metadata.owner"
    assert fact is not None
    assert fact.value == "0 6 * * *"
    assert fact.message_sequence == 1
    assert fact.extraction_method == ExtractionMethod.LLM
    assert fact.confidence == 0.94
    assert gateway.contract["orchestration"]["schedule"] == "0 6 * * *"
    assert gateway.origins["orchestration.schedule"] == Origin.USER
    assert gateway.submission_origins[-1] == Origin.USER


@pytest.mark.asyncio
async def test_stage05_t5_low_confidence_asks_user_without_submit():
    evidence = "Za opiekę nad tym przepływem odpowiada FinOps."
    gateway = RecordingFakeForgeGateway()
    semantic = FakeSemanticResolver(
        [
            ExtractionResult(
                values=[
                    CandidateValue(
                        path="metadata.owner",
                        value="FinOps",
                        confidence=0.79,
                        evidence=evidence,
                    )
                ]
            )
        ]
    )
    service = ADCMOrchestrator(gateway, semantic=semantic)
    turn = await service.start()
    turn = await service.message(turn.session_id, evidence)
    turn = await service.message(turn.session_id, "rocket")

    turn = await service.message(turn.session_id, "customer_daily")

    assert turn.pending_path == "metadata.owner"
    assert {"metadata.owner": "FinOps"} not in gateway.submissions
    assert service.sessions[turn.session_id].get_fact("metadata.owner") is None


@pytest.mark.asyncio
async def test_stage05_t6_user_fact_survives_without_raw_source_message():
    gateway = gateway_with_id_owner_flow()
    semantic = FakeSemanticResolver()
    service = ADCMOrchestrator(gateway, semantic=semantic)
    turn = await service.start()
    memory = service.sessions[turn.session_id]
    memory.remember_fact(
        UserFact(
            path="metadata.owner",
            value="FinOps",
            message_sequence=1,
            extraction_method=ExtractionMethod.LLM,
            confidence=0.96,
            evidence="stara wiadomość spoza okna",
        )
    )
    memory.messages = [message for message in memory.messages if message.role == "assistant"]
    memory.next_message_sequence = 2

    turn = await service.message(turn.session_id, "customer_daily")

    assert turn.status == "complete"
    assert {"metadata.owner": "FinOps"} in gateway.submissions
    assert semantic.calls == []


@pytest.mark.asyncio
async def test_stage06_t1_t2_new_string_and_enum_fields_need_no_path_code():
    gateway = SchemaDrivenFakeForgeGateway(
        [
            Requirement(
                path="metadata.businessDomain",
                question="Jaka jest domena biznesowa?",
                value_schema={"type": "string", "minLength": 2},
            ),
            Requirement(
                path="governance.classification",
                question="Jaka jest klasyfikacja?",
                value_schema={
                    "type": "string",
                    "enum": ["PUBLIC", "INTERNAL", "RESTRICTED"],
                },
            ),
        ]
    )
    service = ADCMOrchestrator(gateway)
    turn = await service.start()

    assert turn.pending_path == "metadata.businessDomain"
    assert turn.pending_requirement is not None
    assert turn.pending_requirement.value_schema["minLength"] == 2

    turn = await service.message(turn.session_id, "finance")
    assert turn.pending_path == "governance.classification"

    turn = await service.message(turn.session_id, "internal")

    assert turn.status == "complete"
    assert gateway.contract["metadata"]["businessDomain"] == "finance"
    assert gateway.contract["governance"]["classification"] == "INTERNAL"


@pytest.mark.asyncio
async def test_stage06_t3_array_object_works_for_an_unseen_path():
    gateway = SchemaDrivenFakeForgeGateway(
        [
            Requirement(
                path="custom.dataset.fields",
                question="Podaj pola.",
                value_schema={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "dataType"],
                        "properties": {
                            "name": {"type": "string"},
                            "dataType": {
                                "type": "string",
                                "enum": ["STRING", "DATE"],
                            },
                        },
                    },
                },
            )
        ]
    )
    service = ADCMOrchestrator(gateway)
    turn = await service.start()

    turn = await service.message(
        turn.session_id,
        "created_at date\ncustomer_id string",
    )

    assert turn.status == "complete"
    assert gateway.contract["custom"]["dataset"]["fields"] == [
        {"name": "created_at", "dataType": "DATE"},
        {"name": "customer_id", "dataType": "STRING"},
    ]


@pytest.mark.asyncio
async def test_stage06_t4_unsupported_schema_neither_guesses_nor_calls_llm():
    requirement = Requirement(
        path="custom.deliveryMode",
        question="Podaj tryb dostawy.",
        value_schema={},
        unsupported_schema_keywords=["anyOf"],
    )
    gateway = SchemaDrivenFakeForgeGateway([requirement])
    semantic = FakeSemanticResolver(
        [
            ExtractionResult(
                values=[
                    CandidateValue(
                        path="custom.deliveryMode",
                        value="invented",
                        confidence=0.99,
                        evidence="batch",
                    )
                ]
            )
        ]
    )
    service = ADCMOrchestrator(gateway, semantic=semantic)
    turn = await service.start()

    assert "nie obsługuje konstrukcji schematu: anyOf" in turn.message
    turn = await service.message(turn.session_id, "batch")

    assert turn.pending_path == "custom.deliveryMode"
    assert semantic.calls == []
    assert {"custom.deliveryMode": "batch"} not in gateway.submissions

    turn = await service.message(turn.session_id, '"batch"')

    assert turn.status == "complete"
    assert gateway.contract["custom"]["deliveryMode"] == "batch"


@pytest.mark.asyncio
async def test_stage07_max_auto_steps_stops_a_progressing_chain():
    gateway = SchemaDrivenFakeForgeGateway(
        [
            Requirement(
                path="custom.first",
                question="first",
                value_schema={"type": "string", "enum": ["A"]},
            ),
            Requirement(
                path="custom.second",
                question="second",
                value_schema={"type": "string", "enum": ["B"]},
            ),
        ]
    )
    service = ADCMOrchestrator(gateway, max_auto_steps=1)
    turn = await service.start()
    memory = service.sessions[turn.session_id]
    memory.remember_fact(
        UserFact(
            path="custom.first",
            value="A",
            message_sequence=1,
            extraction_method=ExtractionMethod.DETERMINISTIC,
        )
    )
    memory.remember_fact(
        UserFact(
            path="custom.second",
            value="B",
            message_sequence=1,
            extraction_method=ExtractionMethod.DETERMINISTIC,
        )
    )

    turn = await service.message(turn.session_id, "unknown")

    assert gateway.submissions == [{"custom.first": "A"}]
    assert turn.pending_path == "custom.second"
    assert turn.candidate_issues[-1]["validator"] == "max_auto_steps"
