"""Testy publicznego kontraktu REST API v1.

Aplikacja jest budowana przez `create_app` na fake'ach — bez zmiennych środowiskowych,
bez MCP i bez zapisu na dysk.
"""

from fastapi.testclient import TestClient

from adcm.adapters.api.app import create_app
from adcm.adapters.response_basic import BasicResponseComposer
from adcm.adapters.session_memory import InMemorySessionRepository
from adcm.application.candidate_policy import CandidatePolicy
from adcm.application.document_engine import DocumentEngine
from adcm.application.external_check_coordinator import ExternalCheckCoordinator
from adcm.application.observability.app_log_recorder import AppLogRecorder
from adcm.application.proposal_reconciler import ProposalReconciler
from adcm.application.rules_engine import ConventionRulesEngine
from adcm.application.session_service import SessionService
from adcm.application.stabilization_engine import StabilizationEngine
from adcm.application.turn_orchestrator import TurnOrchestrator
from adcm.domain.errors import ForgeUnavailableError
from adcm.domain.forge import ContractStatus, Diagnostic, ForgeAnalysis, ForgeDescription, MissingRequirement
from adcm.domain.mutations import CandidateAction, MutationCandidate
from adcm.domain.rules import RulesDocument
from adcm.domain.turn import IntentResolution

TURNS_PATH = "/v1/sessions/{session_id}/turns"
LEGACY_TURN_PATH = "/v1/sessions/{session_id}/turn"


class CaptureSink:
    def __init__(self) -> None:
        self.events = []

    def emit(self, event) -> None:
        self.events.append(event)


class FakeForge:
    """Forge sterowany z testu: status, braki, diagnostyka albo awaria."""

    def __init__(
        self,
        *,
        status: ContractStatus | None = None,
        missing: list[MissingRequirement] | None = None,
        diagnostics: list[Diagnostic] | None = None,
        fail_with: Exception | None = None,
    ) -> None:
        self.status = status or ContractStatus(valid=True, complete=False, clean=True)
        self.missing = missing or []
        self.diagnostics = diagnostics or []
        self.fail_with = fail_with

    async def describe(self, *, correlation_id: str | None = None) -> ForgeDescription:
        if self.fail_with is not None:
            raise self.fail_with
        return ForgeDescription(protocol_version="1.0", definition_version="fake")

    async def analyze(self, document: dict, *, correlation_id: str | None = None) -> ForgeAnalysis:
        if self.fail_with is not None:
            raise self.fail_with
        return ForgeAnalysis(
            protocol_version="1.0",
            definition_version="fake",
            missing=self.missing,
            diagnostics=self.diagnostics,
            status=self.status,
        )


class FakeIntent:
    """Zapisuje wartość pod ścieżką zależną od numeru wywołania."""

    def __init__(self, *, unresolved: list[dict] | None = None) -> None:
        self.unresolved = unresolved or []
        self.calls = 0

    async def resolve(self, message: str, *, document: dict, definition=None) -> IntentResolution:
        self.calls += 1
        return IntentResolution(
            candidates=[
                MutationCandidate(
                    action=CandidateAction.SET,
                    path=f"/metadata/field{self.calls}",
                    value=message,
                    confidence=0.99,
                    evidence=message,
                )
            ],
            unresolved=self.unresolved,
        )


class RulesRepository:
    async def load(self, session_id: str) -> RulesDocument:
        return RulesDocument(version="test", rules=[])


def build_client(*, forge=None, intent=None, debug_api: bool = False) -> TestClient:
    forge = forge or FakeForge()
    intent = intent or FakeIntent()
    app_log = AppLogRecorder(CaptureSink(), environment="test")
    document_engine = DocumentEngine()
    sessions = InMemorySessionRepository()
    orchestrator = TurnOrchestrator(
        sessions=sessions,
        forge=forge,
        intent=intent,
        rules=RulesRepository(),
        response=BasicResponseComposer(),
        candidate_policy=CandidatePolicy(),
        document_engine=document_engine,
        stabilization=StabilizationEngine(
            forge=forge,
            document_engine=document_engine,
            rules_engine=ConventionRulesEngine(),
            proposal_reconciler=ProposalReconciler(),
        ),
        external_checks=ExternalCheckCoordinator(),
        app_log=app_log,
    )
    app = create_app(
        orchestrator=orchestrator,
        session_service=SessionService(sessions=sessions),
        app_log=app_log,
        debug_api=debug_api,
    )
    return TestClient(app, raise_server_exceptions=False)


def create_session(client: TestClient) -> str:
    response = client.post("/v1/sessions")
    assert response.status_code == 201
    return response.json()["session_id"]


def test_health_reports_service_without_calling_forge() -> None:
    # Forge, który zawsze pada — healthcheck nie może go dotykać.
    client = build_client(forge=FakeForge(fail_with=ForgeUnavailableError("down")))
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "adcm"}


def test_create_session_returns_generated_id_and_zero_turn() -> None:
    client = build_client()
    response = client.post("/v1/sessions")
    assert response.status_code == 201
    body = response.json()
    assert body["session_id"]
    assert body["turn_no"] == 0
    assert body["status"] == "created"


def test_created_session_is_readable_and_has_no_contract_status_yet() -> None:
    client = build_client()
    session_id = create_session(client)
    response = client.get(f"/v1/sessions/{session_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == session_id
    assert body["turn_no"] == 0
    assert body["document"] == {}
    assert body["contract_status"] is None
    assert body["missing"] == []


def test_get_unknown_session_returns_standard_404_payload() -> None:
    client = build_client()
    response = client.get("/v1/sessions/not-existing")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "session_not_found"
    assert response.json()["error"]["message"] == "Session not found"


def test_turn_on_unknown_session_returns_404_without_creating_it() -> None:
    client = build_client()
    response = client.post(TURNS_PATH.format(session_id="not-existing"), json={"message": "hello"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "session_not_found"
    # Nieudany turn nie może materializować sesji.
    assert client.get("/v1/sessions/not-existing").status_code == 404


def test_turn_returns_message_document_and_contract_status() -> None:
    client = build_client()
    session_id = create_session(client)
    response = client.post(TURNS_PATH.format(session_id=session_id), json={"message": "sap"})
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == session_id
    assert body["turn_no"] == 1
    assert body["message"]
    assert body["document"] == {"metadata": {"field1": "sap"}}
    assert body["contract_status"] == {"valid": True, "complete": False, "clean": True}
    assert body["correlation_id"]


def test_multiple_turns_share_session_and_preserve_state() -> None:
    client = build_client()
    session_id = create_session(client)
    first = client.post(TURNS_PATH.format(session_id=session_id), json={"message": "sap"}).json()
    second = client.post(TURNS_PATH.format(session_id=session_id), json={"message": "sap_id"}).json()

    assert first["session_id"] == second["session_id"] == session_id
    assert first["turn_no"] == 1
    assert second["turn_no"] == 2
    # Wartość z pierwszej tury przetrwała drugą.
    assert second["document"] == {"metadata": {"field1": "sap", "field2": "sap_id"}}

    state = client.get(f"/v1/sessions/{session_id}").json()
    assert state["turn_no"] == 2
    assert state["document"] == second["document"]
    assert state["contract_status"] == second["contract_status"]


def test_unresolved_intent_reaches_api_response() -> None:
    intent = FakeIntent(
        unresolved=[{"intent": "włącz target bronze", "reason": "No contract path matching target/bronze"}]
    )
    client = build_client(intent=intent)
    session_id = create_session(client)
    body = client.post(
        TURNS_PATH.format(session_id=session_id), json={"message": "włącz target bronze"}
    ).json()
    assert body["unresolved"] == [
        {"intent": "włącz target bronze", "reason": "No contract path matching target/bronze"}
    ]


def test_unresolved_accepts_resolver_value_key() -> None:
    # Resolver heurystyczny opisuje nierozpoznany fragment kluczem `value`.
    intent = FakeIntent(unresolved=[{"value": "separator=;", "reason": "source type is not known"}])
    client = build_client(intent=intent)
    session_id = create_session(client)
    body = client.post(TURNS_PATH.format(session_id=session_id), json={"message": "separator=;"}).json()
    assert body["unresolved"] == [{"intent": "separator=;", "reason": "source type is not known"}]


def test_missing_and_diagnostics_are_mapped_to_public_shape() -> None:
    forge = FakeForge(
        missing=[
            MissingRequirement(
                path="/metadata/dataFileId",
                code="required",
                message="Required value missing",
                expected_type="string",
            )
        ],
        diagnostics=[Diagnostic(code="bad_value", path="/x", severity="error", message="nope")],
    )
    client = build_client(forge=forge)
    session_id = create_session(client)
    body = client.post(TURNS_PATH.format(session_id=session_id), json={"message": "sap"}).json()
    assert body["missing"] == [
        {"path": "/metadata/dataFileId", "code": "required", "message": "Required value missing"}
    ]
    assert body["diagnostics"] == [
        {"code": "bad_value", "path": "/x", "severity": "error", "message": "nope"}
    ]


def test_complete_contract_status_is_reflected_faithfully() -> None:
    client = build_client(forge=FakeForge(status=ContractStatus(valid=True, complete=True, clean=True)))
    session_id = create_session(client)
    body = client.post(TURNS_PATH.format(session_id=session_id), json={"message": "sap"}).json()
    assert body["contract_status"] == {"valid": True, "complete": True, "clean": True}
    assert body["missing"] == []


def test_changes_expose_operation_and_path_only() -> None:
    client = build_client()
    session_id = create_session(client)
    body = client.post(TURNS_PATH.format(session_id=session_id), json={"message": "sap"}).json()
    assert body["changes"] == [
        {"operation": "add", "path": "/metadata/field1", "old_value": None, "new_value": "sap"}
    ]


def test_forge_failure_maps_to_503_without_leaking_internals() -> None:
    forge = FakeForge(fail_with=ForgeUnavailableError("http://internal-forge:8000/mcp refused"))
    client = build_client(forge=forge)
    session_id = create_session(client)
    response = client.post(TURNS_PATH.format(session_id=session_id), json={"message": "sap"})
    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == "contract_forge_unavailable"
    assert error["message"] == "Contract validation service is temporarily unavailable"
    assert error["correlation_id"]
    raw = response.text
    assert "Traceback" not in raw
    assert "internal-forge" not in raw
    assert "detail" not in response.json()


def test_unexpected_failure_maps_to_500_without_leaking_internals() -> None:
    forge = FakeForge(fail_with=RuntimeError("secret://credentials leaked"))
    client = build_client(forge=forge)
    session_id = create_session(client)
    response = client.post(TURNS_PATH.format(session_id=session_id), json={"message": "sap"})
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "secret" not in response.text


def test_invalid_turn_payloads_are_rejected_with_4xx() -> None:
    client = build_client()
    session_id = create_session(client)
    path = TURNS_PATH.format(session_id=session_id)
    for payload in ({}, {"message": ""}, {"message": "   "}, {"message": "ok", "extra": 1}):
        response = client.post(path, json=payload)
        assert response.status_code == 422, payload
        assert response.json()["error"]["code"] == "validation_error", payload


def test_legacy_turn_alias_returns_the_same_contract() -> None:
    client = build_client()
    session_id = create_session(client)
    legacy = client.post(LEGACY_TURN_PATH.format(session_id=session_id), json={"message": "sap"})
    canonical = client.post(TURNS_PATH.format(session_id=session_id), json={"message": "sap_id"})
    assert legacy.status_code == canonical.status_code == 200
    assert legacy.json().keys() == canonical.json().keys()
    assert legacy.json()["turn_no"] == 1
    assert canonical.json()["turn_no"] == 2


def test_turn_response_does_not_expose_internal_state() -> None:
    client = build_client()
    session_id = create_session(client)
    body = client.post(TURNS_PATH.format(session_id=session_id), json={"message": "sap"}).json()
    assert set(body) == {
        "session_id",
        "turn_no",
        "message",
        "document",
        "contract_status",
        "missing",
        "diagnostics",
        "unresolved",
        "changes",
        "correlation_id",
    }
    for leaked in ("forge", "stabilization", "new_events", "external_checks"):
        assert leaked not in body


def test_session_state_does_not_expose_provenance_or_mutation_log() -> None:
    client = build_client()
    session_id = create_session(client)
    client.post(TURNS_PATH.format(session_id=session_id), json={"message": "sap"})
    response = client.get(f"/v1/sessions/{session_id}")
    assert set(response.json()) == {
        "session_id",
        "turn_no",
        "document",
        "contract_status",
        "missing",
        "diagnostics",
    }
    assert "mutation_log" not in response.text
    assert "provenance" not in response.text


def test_correlation_id_header_is_returned_and_matches_body() -> None:
    client = build_client()
    session_id = create_session(client)
    response = client.post(TURNS_PATH.format(session_id=session_id), json={"message": "sap"})
    assert response.headers["X-Correlation-ID"] == response.json()["correlation_id"]


def test_openapi_documents_the_public_contract() -> None:
    client = build_client()
    schema = client.get("/openapi.json")
    assert schema.status_code == 200
    spec = schema.json()
    paths = spec["paths"]
    for path in ("/health", "/v1/sessions", "/v1/sessions/{session_id}", TURNS_PATH, LEGACY_TURN_PATH):
        assert path in paths, path
    assert paths[LEGACY_TURN_PATH]["post"].get("deprecated") is True
    assert paths[TURNS_PATH]["post"].get("deprecated") is not True
    for schema_name in ("TurnResponse", "TurnRequest", "ErrorResponse", "SessionStateResponse"):
        assert schema_name in spec["components"]["schemas"], schema_name
    assert "503" in paths[TURNS_PATH]["post"]["responses"]


def test_debug_endpoint_is_absent_unless_enabled() -> None:
    client = build_client()
    session_id = create_session(client)
    assert client.get(f"/v1/debug/sessions/{session_id}").status_code == 404


def test_debug_endpoint_exposes_internal_state_when_enabled() -> None:
    client = build_client(debug_api=True)
    session_id = create_session(client)
    client.post(TURNS_PATH.format(session_id=session_id), json={"message": "sap"})
    response = client.get(f"/v1/debug/sessions/{session_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["contract"]["mutation_log"]
    assert client.get("/v1/debug/sessions/nope").status_code == 404
