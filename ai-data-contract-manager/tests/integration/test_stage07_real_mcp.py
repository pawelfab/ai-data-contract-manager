from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterator

import pytest
from fastapi.testclient import TestClient

from adcm.api import create_app
from adcm.gateway import MCPForgeGateway
from adcm.models import ChatMessage, Origin, Requirement, UserFact
from adcm.orchestrator import ADCMOrchestrator
from adcm.semantic import CandidateValue, ExtractionResult, SemanticResolver


REPO_ROOT = Path(__file__).resolve().parents[3]
ADCM_ROOT = REPO_ROOT / "ai-data-contract-manager"
FORGE_ROOT = REPO_ROOT / "mcp-servers" / "mcp-contract-forge"
DEFAULT_SCHEMA = FORGE_ROOT / "config" / "contract.json"
DEFAULT_RULES = FORGE_ROOT / "config" / "ux_rules_contract_v1.json"


def _venv_python(service_root: Path) -> Path:
    windows = service_root / ".venv" / "Scripts" / "python.exe"
    posix = service_root / ".venv" / "bin" / "python"
    return windows if windows.exists() else posix


def _free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _wait_for_port(process: subprocess.Popen[Any], port: int) -> None:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if process.poll() is not None:
            pytest.fail(f"Contract Forge exited during startup with code {process.returncode}")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.1)
    pytest.fail(f"Contract Forge did not listen on port {port}")


@contextmanager
def _running_forge(schema_path: Path = DEFAULT_SCHEMA) -> Iterator[str]:
    forge_python = _venv_python(FORGE_ROOT)
    if not forge_python.exists():
        pytest.skip("Contract Forge virtual environment is unavailable")

    port = _free_port()
    environment = os.environ.copy()
    environment.update(
        {
            "CONTRACT_FORGE_HOST": "127.0.0.1",
            "CONTRACT_FORGE_PORT": str(port),
            "CONTRACT_FORGE_SCHEMA_PATH": str(schema_path),
            "CONTRACT_FORGE_RULES_PATH": str(DEFAULT_RULES),
            "PYTHONIOENCODING": "utf-8",
        }
    )
    creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    process = subprocess.Popen(
        [str(forge_python), "-m", "contract_forge.mcp_server"],
        cwd=FORGE_ROOT,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags,
    )
    try:
        _wait_for_port(process, port)
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


@pytest.fixture(scope="module")
def forge_url() -> Iterator[str]:
    with _running_forge() as url:
        yield url


class RecordingMCPForgeGateway(MCPForgeGateway):
    def __init__(self, url: str):
        super().__init__(url)
        self.submissions: list[dict[str, Any]] = []
        self.submission_origins: list[Origin] = []

    async def submit_values(
        self,
        session_id: str,
        values: dict[str, Any],
        origin: Origin,
    ):
        self.submissions.append(deepcopy(values))
        self.submission_origins.append(origin)
        return await super().submit_values(session_id, values, origin)


class FakeSemanticResolver(SemanticResolver):
    def __init__(self, results: list[ExtractionResult] | None = None):
        self.results = list(results or [])
        self.calls: list[dict[str, Any]] = []

    async def extract_from_history(
        self,
        session_id: str,
        messages: list[ChatMessage],
        pending: list[Requirement],
        overridable: list[Requirement],
        user_facts: list[UserFact],
    ) -> ExtractionResult:
        self.calls.append(
            {
                "session_id": session_id,
                "messages": deepcopy(messages),
                "pending": [field.path for field in pending],
                "overridable": [field.path for field in overridable],
                "facts": deepcopy(user_facts),
            }
        )
        return self.results.pop(0) if self.results else ExtractionResult()


@pytest.mark.asyncio
async def test_stage07_a_reuses_one_rich_message_and_overrides_schedule(forge_url: str):
    gateway = RecordingMCPForgeGateway(forge_url)
    semantic = FakeSemanticResolver()
    service = ADCMOrchestrator(gateway, semantic=semantic)

    async with gateway:
        turn = await service.start()
        assert turn.pending_path == "metadata.sourceSystemGcpId"
        assert [field.path for field in (await service.state(turn.session_id)).pending] == [
            "metadata.sourceSystemGcpId"
        ]

        turn = await service.message(
            turn.session_id,
            "source system: SAP\n"
            "pipeline: sap_orders_daily\n"
            "owner: finance@example.com\n"
            "uri: gs://raw-zone/sap/orders.csv\n"
            "schedule: 0 6 * * *\n"
            "order_id STRING\n"
            "amount NUMERIC",
        )
        state = await service.state(turn.session_id)

    assert turn.status == "complete"
    assert turn.contract["metadata"]["id"] == "sap_orders_daily"
    assert turn.contract["metadata"]["owner"] == "finance@example.com"
    assert turn.contract["source"]["columns"] == [
        {"name": "order_id", "dataType": "STRING", "nullable": True},
        {"name": "amount", "dataType": "NUMERIC", "nullable": True},
    ]
    assert turn.contract["orchestration"]["schedule"] == "0 6 * * *"
    assert state.origins["orchestration.schedule"] == Origin.USER.value
    assert "source.columns" not in {field.path for field in state.overridable}
    assert semantic.calls == []
    assert gateway.submission_origins == [Origin.USER] * len(gateway.submissions)


@pytest.mark.asyncio
async def test_stage07_b_latest_owner_is_the_only_owner_submitted(forge_url: str):
    gateway = RecordingMCPForgeGateway(forge_url)
    service = ADCMOrchestrator(gateway)

    async with gateway:
        turn = await service.start()
        turn = await service.message(turn.session_id, "owner team_a")
        turn = await service.message(turn.session_id, "owner jednak team_b")
        turn = await service.message(turn.session_id, "sap")
        turn = await service.message(turn.session_id, "stage07_owner_correction")
        turn = await service.message(turn.session_id, "gs://raw-zone/sap/correction.csv")
        turn = await service.message(turn.session_id, "customer_id STRING")
        state = await service.state(turn.session_id)

    owner_submissions = [
        submission["metadata.owner"]
        for submission in gateway.submissions
        if "metadata.owner" in submission
    ]
    fact = service.sessions[turn.session_id].get_fact("metadata.owner")
    assert turn.status == "complete"
    assert owner_submissions == ["team_b"]
    assert fact is not None and fact.value == "team_b" and fact.message_sequence == 2
    assert turn.contract["metadata"]["owner"] == "team_b"
    assert state.origins["metadata.owner"] == Origin.USER.value


@pytest.mark.asyncio
async def test_stage07_b_can_correct_owner_after_it_reached_forge(forge_url: str):
    gateway = RecordingMCPForgeGateway(forge_url)
    service = ADCMOrchestrator(gateway)

    async with gateway:
        turn = await service.start()
        turn = await service.message(turn.session_id, "sap")
        turn = await service.message(turn.session_id, "stage07_existing_owner")
        turn = await service.message(turn.session_id, "owner team_a")
        assert turn.contract["metadata"]["owner"] == "team_a"

        turn = await service.message(turn.session_id, "owner jednak team_b")
        turn = await service.message(turn.session_id, "gs://raw-zone/sap/owner.csv")
        turn = await service.message(turn.session_id, "customer_id STRING")
        state = await service.state(turn.session_id)

    owner_submissions = [
        submission["metadata.owner"]
        for submission in gateway.submissions
        if "metadata.owner" in submission
    ]
    assert turn.status == "complete"
    assert owner_submissions == ["team_a", "team_b"]
    assert turn.contract["metadata"]["owner"] == "team_b"
    assert state.origins["metadata.owner"] == Origin.USER.value


@pytest.mark.asyncio
async def test_stage07_c_partial_columns_are_merged_before_forge_submit(forge_url: str):
    gateway = RecordingMCPForgeGateway(forge_url)
    service = ADCMOrchestrator(gateway)

    async with gateway:
        turn = await service.start()
        for answer in (
            "sap",
            "stage07_partial_columns",
            "data-team",
            "gs://raw-zone/sap/partial.csv",
        ):
            turn = await service.message(turn.session_id, answer)
        submissions_before = len(gateway.submissions)

        turn = await service.message(turn.session_id, "data_d, sap1, sap2, sap3")
        partial = service.sessions[turn.session_id].get_partial("source.columns")

        assert len(gateway.submissions) == submissions_before
        assert partial is not None and partial.missing == ["dataType"]
        assert "dataType dla: data_d, sap1, sap2, sap3" in turn.message

        turn = await service.message(
            turn.session_id,
            "data_d DATE\nsap1 STRING\nsap2 STRING\nsap3 NUMERIC",
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
async def test_stage07_d_llm_is_bounded_fallback_after_deterministic_steps(forge_url: str):
    evidence = "Za opiekę nad tym przepływem odpowiada FinOps."
    semantic = FakeSemanticResolver(
        [
            ExtractionResult(
                values=[
                    CandidateValue(
                        path="targets.gold.secret",
                        value="invented",
                        confidence=0.99,
                        evidence=evidence,
                    ),
                    CandidateValue(
                        path="metadata.owner",
                        value="FinOps",
                        confidence=0.96,
                        evidence=evidence,
                    ),
                ]
            )
        ]
    )
    gateway = RecordingMCPForgeGateway(forge_url)
    service = ADCMOrchestrator(gateway, semantic=semantic)

    async with gateway:
        turn = await service.start()
        turn = await service.message(turn.session_id, evidence)
        turn = await service.message(turn.session_id, "sap")
        assert turn.pending_path == "metadata.id"
        assert semantic.calls == []

        turn = await service.message(turn.session_id, "stage07_semantic_fallback")
        assert semantic.calls
        turn = await service.message(turn.session_id, "gs://raw-zone/sap/semantic.csv")
        turn = await service.message(turn.session_id, "customer_id STRING")
        state = await service.state(turn.session_id)

    assert turn.status == "complete"
    assert turn.contract["metadata"]["owner"] == "FinOps"
    assert state.origins["metadata.owner"] == Origin.USER.value
    assert all("targets.gold.secret" not in submission for submission in gateway.submissions)
    assert {"metadata.owner": "FinOps"} in gateway.submissions


@pytest.mark.asyncio
async def test_stage07_e_new_required_string_works_over_real_mcp(
    tmp_path: Path,
):
    schema = json.loads(DEFAULT_SCHEMA.read_text(encoding="utf-8"))
    metadata = schema["$defs"]["Metadata"]
    metadata["required"].append("businessDomain")
    metadata["properties"]["businessDomain"] = {
        "type": "string",
        "minLength": 2,
        "description": "Domena biznesowa danych.",
        "x-acdm-question": "Jaka jest domena biznesowa?",
    }
    schema_path = tmp_path / "stage07.contract.json"
    schema_path.write_text(json.dumps(schema, ensure_ascii=False), encoding="utf-8")

    with _running_forge(schema_path) as url:
        gateway = RecordingMCPForgeGateway(url)
        service = ADCMOrchestrator(gateway)
        answers: dict[str, str] = {
            "metadata.sourceSystemGcpId": "sap",
            "metadata.id": "stage07_dynamic_schema",
            "metadata.owner": "data-team",
            "metadata.businessDomain": "finance",
            "source.uri": "gs://raw-zone/sap/dynamic.csv",
            "source.columns": "customer_id STRING",
        }

        async with gateway:
            turn = await service.start()
            while turn.status == "needs_input":
                assert turn.pending_path in answers
                turn = await service.message(
                    turn.session_id,
                    answers[turn.pending_path],
                )

    assert turn.status == "complete"
    assert turn.contract["metadata"]["businessDomain"] == "finance"
    assert {"metadata.businessDomain": "finance"} in gateway.submissions


@pytest.mark.asyncio
async def test_unknown_source_system_uses_generic_path_over_real_mcp(forge_url: str):
    gateway = RecordingMCPForgeGateway(forge_url)
    service = ADCMOrchestrator(gateway)

    async with gateway:
        turn = await service.start()
        assert turn.pending_requirement is not None
        assert turn.pending_requirement.allowed_values == ["rocket", "sap"]
        assert turn.pending_requirement.allow_custom_value is True

        turn = await service.message(turn.session_id, "oracle_erp")
        state_after_system = await service.state(turn.session_id)

        assert turn.pending_path == "source.sourceType"
        assert turn.contract["metadata"]["sourceSystemGcpId"] == "ORACLE_ERP"
        assert Origin.SYSTEM_ENRICHMENT.value not in state_after_system.origins.values()
        assert "schedule" not in turn.contract["orchestration"]

        answers: dict[str, str] = {
            "source.sourceType": "csv",
            "metadata.id": "oracle_orders_daily",
            "metadata.owner": "data-team",
            "source.uri": "gs://raw-zone/oracle/orders.csv",
            "source.columns": "order_id STRING\namount NUMERIC",
            "orchestration.schedule": "0 4 * * *",
        }
        while turn.status == "needs_input":
            assert turn.pending_path in answers
            turn = await service.message(
                turn.session_id,
                answers[turn.pending_path],
            )
        final_state = await service.state(turn.session_id)

    assert turn.status == "complete"
    assert turn.contract["source"]["sourceType"] == "csv"
    assert "options" not in turn.contract["source"]
    assert "converter" not in turn.contract
    assert "preparator" not in turn.contract
    assert turn.contract["metadata"]["version"] == "1.0.0"
    assert turn.contract["targets"]["bronze"]["table"]["dataset"] == (
        "oracle_erp_bronze"
    )
    assert turn.contract["orchestration"]["timezone"] == "Europe/Warsaw"
    assert turn.contract["orchestration"]["schedule"] == "0 4 * * *"
    assert Origin.SYSTEM_ENRICHMENT.value not in final_state.origins.values()
    assert final_state.origins["targets.bronze.table.dataset"] == (
        Origin.GENERIC_ENRICHMENT.value
    )
    assert final_state.origins["metadata.version"] == Origin.SCHEMA_DEFAULT.value


def test_stage07_api_smoke_uses_real_mcp_transport(forge_url: str):
    gateway = RecordingMCPForgeGateway(forge_url)
    app = create_app(ADCMOrchestrator(gateway))

    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        started = client.post("/sessions")
        assert started.status_code == 200
        body = started.json()
        assert body["pending_path"] == "metadata.sourceSystemGcpId"

        answered = client.post(
            f"/sessions/{body['session_id']}/messages",
            json={"message": "sap"},
        )
        assert answered.status_code == 200
        assert answered.json()["contract"]["source"]["sourceType"] == "csv"


def test_stage07_cli_smoke_uses_real_mcp_transport(forge_url: str):
    adcm_python = _venv_python(ADCM_ROOT)
    environment = os.environ.copy()
    environment.update(
        {
            "ADCM_MCP_URL": forge_url,
            "ADCM_LLM_MODE": "local",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    completed = subprocess.run(
        [str(adcm_python), "-m", "adcm.cli"],
        cwd=ADCM_ROOT,
        env=environment,
        input=(
            "sap\n"
            "stage07_cli_smoke\n"
            "data-team\n"
            "gs://raw-zone/sap/cli.csv\n"
            "customer_id STRING\n"
            "amount NUMERIC\n"
            "\n"
        ),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )

    assert completed.returncode == 0, completed.stderr
    assert "FINAL CONTRACT" in completed.stdout
    final_contract = json.loads(completed.stdout.split("--- FINAL CONTRACT ---", 1)[1])
    assert final_contract["metadata"]["id"] == "stage07_cli_smoke"
