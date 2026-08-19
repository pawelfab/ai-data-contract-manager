from pathlib import Path

from contract_forge.engine import ContractForge
from contract_forge.models import Origin

ROOT = Path(__file__).resolve().parents[1]


def build_forge():
    return ContractForge.from_files(
        ROOT / "config" / "contract.json",
        ROOT / "config" / "ux_rules_contract_v1.json",
        deploy_env="dev",
    )


def test_rocket_happy_path():
    forge = build_forge()
    state = forge.start_session()
    assert state.pending[0].path == "metadata.sourceSystemGcpId"
    assert state.pending[0].input_mode == "explicit"

    state = forge.submit_values(state.session_id, {"metadata.sourceSystemGcpId": "rocket"}, Origin.USER)
    assert state.contract["source"]["sourceType"] == "fixed_width"
    assert state.contract["targets"]["bronze"]["table"]["dataset"] == "rocket_bronze"
    assert state.pending[0].path == "metadata.id"
    assert state.pending[0].input_mode == "explicit"

    sid = state.session_id
    state = forge.submit_values(sid, {"metadata.id": "customer_accounts_daily"}, Origin.USER)
    state = forge.submit_values(sid, {"metadata.owner": "data-platform@example.com"}, Origin.USER)
    state = forge.submit_values(sid, {"source.uri": "gs://raw-zone/accounts/accounts.dat"}, Origin.USER)
    state = forge.submit_values(
        sid,
        {
            "source.columns": [
                {"name": "account_id", "start": 0, "end": 8, "dataType": "STRING", "nullable": False},
                {"name": "balance", "start": 8, "end": 20, "dataType": "NUMERIC"},
            ]
        },
        Origin.USER,
    )

    assert state.status == "complete", state.validation_errors
    assert state.contract["metadata"]["version"] == "1.0.0"
    assert state.contract["converter"]["output"]["format"] == "parquet"
    assert state.contract["orchestration"]["dagId"] == "customer_accounts_daily"
    assert state.contract["orchestration"]["schedule"] == "0 0 * * *"
    assert state.contract["targets"]["bronze"]["table"]["project"] == "pekao-prj-dev-core-intg-01"
    assert state.contract["targets"]["bronze"]["columns"][0]["sourcePath"] == "source.columns.account_id"
    assert state.contract["targets"]["bronze"]["columns"][0]["mode"] == "REQUIRED"


def test_sap_enrichment():
    forge = build_forge()
    state = forge.start_session()
    sid = state.session_id
    state = forge.submit_values(sid, {"metadata.sourceSystemGcpId": "sap"}, Origin.USER)
    assert state.contract["source"]["sourceType"] == "csv"
    assert state.contract["source"]["options"]["delimiter"] == "|"
    assert state.contract["source"]["options"]["file"]["encoding"] == "ISO-8859-2"
    assert state.contract["preparator"]["enabled"] is False


def test_unknown_source_system_skips_system_enrichment_and_asks_for_source_type():
    forge = build_forge()
    started = forge.start_session()
    requirement = started.pending[0]

    assert requirement.allowed_values == ["rocket", "sap"]
    assert requirement.allow_custom_value is True
    assert "enum" not in requirement.value_schema

    state = forge.submit_values(
        started.session_id,
        {"metadata.sourceSystemGcpId": "oracle_erp"},
        Origin.USER,
    )

    assert state.source_system == "oracle_erp"
    assert state.contract["metadata"]["sourceSystemGcpId"] == "ORACLE_ERP"
    assert state.pending[0].path == "source.sourceType"
    assert set(state.pending[0].allowed_values or []) == {
        "csv",
        "fixed_width",
        "jdbc",
        "json",
        "txt",
    }
    assert "schedule" not in state.contract["orchestration"]
    assert Origin.SYSTEM_ENRICHMENT.value not in state.origins.values()
    assert state.contract["metadata"]["version"] == "1.0.0"
    assert state.contract["targets"]["bronze"]["table"]["dataset"] == (
        "oracle_erp_bronze"
    )


def test_legacy_rules_are_reported_not_silently_remapped():
    forge = ContractForge.from_files(
        ROOT / "config" / "contract.json",
        ROOT / "config" / "ux_rules_original.json",
        deploy_env="dev",
    )
    state = forge.start_session()
    state = forge.submit_values(
        state.session_id,
        {"metadata.sourceSystemGcpId": "rocket"},
        Origin.USER,
    )
    assert state.rule_issues
    bad_paths = {issue.path for issue in state.rule_issues if issue.path}
    assert "bronzeTable.table.project" in bad_paths or "converter.source.fixedWidth.encoding" in bad_paths


def test_forge_owns_canonical_contract_and_not_conversation_history():
    forge = build_forge()
    state = forge.start_session()
    session_id = state.session_id
    state = forge.submit_values(
        session_id,
        {"metadata.sourceSystemGcpId": "rocket"},
        Origin.USER,
    )
    state = forge.submit_values(
        session_id,
        {"metadata.id": "customer_accounts_daily"},
        Origin.USER,
    )

    state.contract["metadata"]["id"] = "mutated_snapshot"
    fresh_state = forge.get_state(session_id)

    assert fresh_state.contract["metadata"]["id"] == "customer_accounts_daily"
    assert forge.sessions[session_id].contract["metadata"]["id"] == "customer_accounts_daily"
    assert "messages" not in type(forge.sessions[session_id]).model_fields
