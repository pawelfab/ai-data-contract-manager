"""Editing the contract at any point in the conversation.

`complete` means the current contract version is complete and valid, not that the
session is closed.
"""

from pathlib import Path

from contract_forge.engine import ContractForge
from contract_forge.models import Origin

ROOT = Path(__file__).resolve().parents[1]

ANSWERS = {
    "metadata.id": "moj_pipeline",
    "metadata.owner": "data-platform@example.com",
    "source.uri": "gs://raw/accounts.csv",
    "source.columns": [
        {"name": "account_id", "dataType": "STRING"},
        {"name": "amount", "dataType": "NUMERIC"},
    ],
    "targets.bronze.columns": [{"name": "account_id", "dataType": "STRING", "mode": "NULLABLE"}],
    "orchestration.schedule": "0 0 * * *",
}


def build_forge() -> ContractForge:
    return ContractForge.from_files(
        ROOT / "config" / "contract.json",
        ROOT / "config" / "ux_rules_contract_v1.json",
        deploy_env="dev",
    )


def complete_session(system: str = "sap") -> tuple[ContractForge, str]:
    forge = build_forge()
    state = forge.start_session()
    session_id = state.session_id
    forge.submit_values(session_id, {"metadata.sourceSystemGcpId": system}, Origin.USER)
    for _ in range(30):
        state = forge.get_state(session_id)
        if state.status != "needs_input":
            break
        path = state.pending[0].path
        assert path in ANSWERS, f"test fixture has no answer for {path}"
        forge.submit_values(session_id, {path: ANSWERS[path]}, Origin.USER)
    assert state.status == "complete", state.validation_errors
    return forge, session_id


def test_editable_lists_leaves_and_whole_arrays_but_never_array_subpaths():
    forge, session_id = complete_session()

    paths = {field.path for field in forge.editable_fields(session_id)}

    assert "source.columns" in paths
    assert not any(".0." in path for path in paths)
    # Containers are not edit units; their leaves are.
    assert "targets.bronze.table" not in paths
    assert "targets.bronze.table.dataset" in paths


def test_editable_ignores_provenance_unlike_overridable():
    """A value the user stated is just as editable as one Forge derived."""
    forge, session_id = complete_session()

    editable = {field.path: field for field in forge.editable_fields(session_id)}
    overridable = {field.path for field in forge.get_state(session_id).overridable}

    for path in ("metadata.id", "source.columns", "metadata.sourceSystemGcpId"):
        assert path in editable
        assert path not in overridable

    assert editable["metadata.owner"].current_value == "data-platform@example.com"
    assert editable["metadata.owner"].current_origin == Origin.USER
    assert editable["source.columns"].value_schema["type"] == "array"
    assert editable["orchestration.retries"].current_origin == Origin.SCHEMA_DEFAULT


def test_user_can_change_a_field_that_is_neither_pending_nor_overridable():
    forge, session_id = complete_session()

    state = forge.submit_values(session_id, {"metadata.id": "inny_pipeline"}, Origin.USER)

    assert state.contract["metadata"]["id"] == "inny_pipeline"
    assert state.candidate_issues == []
    assert state.status == "complete"


def test_an_array_is_replaced_as_one_unit():
    forge, session_id = complete_session()
    columns = [
        *ANSWERS["source.columns"],
        {"name": "created_at", "dataType": "TIMESTAMP"},
    ]

    state = forge.submit_values(session_id, {"source.columns": columns}, Origin.USER)

    assert [column["name"] for column in state.contract["source"]["columns"]] == [
        "account_id",
        "amount",
        "created_at",
    ]
    assert state.status == "complete"


def test_user_can_add_a_section_that_did_not_exist_and_rules_reopen_the_contract():
    forge, session_id = complete_session()
    assert forge.get_state(session_id).contract["preparator"] == {"enabled": False}

    state = forge.submit_values(session_id, {"preparator.enabled": True}, Origin.USER)

    # x-contract-rules now demand an operation, so a complete contract stops being valid.
    assert state.status == "invalid"
    blocking = [
        issue.rule_id
        for issue in state.contract_rule_issues
        if issue.status in {"invalid", "forbidden"}
    ]
    assert blocking == ["preparator.enabled_requires_operation"]

    state = forge.submit_values(
        session_id,
        {"preparator.operations": {"unpack": {"enabled": True, "format": "zip"}}},
        Origin.USER,
    )
    assert state.status == "complete"


def test_changing_an_input_refreshes_the_values_derived_from_it():
    """Enrichment is fill-only, so a corrected input must invalidate what it fed."""
    forge, session_id = complete_session()
    assert [
        column["name"]
        for column in forge.get_state(session_id).contract["targets"]["bronze"]["columns"]
    ] == ["account_id", "amount"]

    state = forge.submit_values(
        session_id,
        {"source.columns": [*ANSWERS["source.columns"], {"name": "created_at", "dataType": "TIMESTAMP"}]},
        Origin.USER,
    )

    assert [column["name"] for column in state.contract["targets"]["bronze"]["columns"]] == [
        "account_id",
        "amount",
        "created_at",
    ]

    state = forge.submit_values(session_id, {"metadata.id": "nowa_nazwa"}, Origin.USER)
    assert state.contract["orchestration"]["dagId"] == "nowa_nazwa"
    assert state.contract["targets"]["bronze"]["table"]["table"] == "nowa_nazwa"


def test_a_user_owned_derived_value_survives_a_change_to_its_input():
    forge, session_id = complete_session()
    forge.submit_values(session_id, {"orchestration.dagId": "moj_wlasny_dag"}, Origin.USER)

    state = forge.submit_values(session_id, {"metadata.id": "jeszcze_inna"}, Origin.USER)

    assert state.contract["orchestration"]["dagId"] == "moj_wlasny_dag"
    assert state.origins["orchestration.dagId"] == Origin.USER.value


def test_unknown_paths_are_still_rejected():
    forge, session_id = complete_session()

    state = forge.submit_values(session_id, {"metadata.unknown": "value"}, Origin.USER)

    assert "unknown" not in state.contract["metadata"]
    assert state.candidate_issues[0].validator == "path"


def test_changing_the_source_system_recomputes_derived_values_and_keeps_user_ones():
    forge, session_id = complete_session("sap")
    before = forge.get_state(session_id).contract
    assert before["targets"]["bronze"]["table"]["dataset"] == "sap_bronze"
    assert before["source"]["sourceType"] == "csv"

    state = forge.submit_values(
        session_id,
        {"metadata.sourceSystemGcpId": "rocket"},
        Origin.USER,
    )

    # Everything the user stated survives; only derived values are recalculated.
    assert state.contract["metadata"]["id"] == "moj_pipeline"
    assert state.contract["metadata"]["owner"] == "data-platform@example.com"
    assert state.contract["source"]["uri"] == "gs://raw/accounts.csv"
    assert state.contract["targets"]["bronze"]["table"]["dataset"] == "rocket_bronze"
    assert state.contract["source"]["sourceType"] == "fixed_width"

    # CSV-only options do not belong to the fixed-width variant any more.
    assert "delimiter" not in state.contract["source"].get("options", {})
    discarded = {entry.path: entry for entry in state.discarded}
    assert discarded["source.options.delimiter"].previous_value == "|"
    assert discarded["targets.bronze.table.dataset"].previous_value == "sap_bronze"
    # Values the recompute restored identically are not reported as lost.
    assert "orchestration.timezone" not in discarded

    # The new variant needs more input, so the normal stair-step loop resumes.
    assert state.status == "needs_input"
    # Fixed-width columns need character ranges the CSV variant never asked for.
    assert {requirement.path for requirement in state.pending} == {
        "source.columns.0.start",
        "source.columns.0.end",
        "source.columns.1.start",
        "source.columns.1.end",
    }


def test_resubmitting_the_same_source_system_does_not_recompute():
    forge, session_id = complete_session("sap")

    state = forge.submit_values(
        session_id,
        {"metadata.sourceSystemGcpId": "sap"},
        Origin.USER,
    )

    assert state.discarded == []
    assert state.status == "complete"
    assert state.contract["targets"]["bronze"]["table"]["dataset"] == "sap_bronze"


def test_discarded_is_cleared_between_submissions():
    forge, session_id = complete_session("sap")
    assert forge.submit_values(
        session_id, {"metadata.sourceSystemGcpId": "rocket"}, Origin.USER
    ).discarded

    state = forge.submit_values(session_id, {"metadata.owner": "nowy@example.com"}, Origin.USER)

    assert state.discarded == []
