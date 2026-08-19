from pathlib import Path

from contract_forge.engine import ContractForge
from contract_forge.models import Origin
from contract_forge.path_utils import write_value

ROOT = Path(__file__).resolve().parents[1]


def build_forge() -> ContractForge:
    return ContractForge.from_files(
        ROOT / "config" / "contract.json",
        ROOT / "config" / "ux_rules_contract_v1.json",
        deploy_env="dev",
    )


def start_rocket() -> tuple[ContractForge, str]:
    forge = build_forge()
    state = forge.start_session()
    state = forge.submit_values(
        state.session_id,
        {"metadata.sourceSystemGcpId": "rocket"},
        Origin.USER,
    )
    return forge, state.session_id


def test_user_overrides_system_enrichment_and_keeps_provenance():
    forge, session_id = start_rocket()
    initial = forge.get_state(session_id)

    assert initial.contract["orchestration"]["schedule"] == "0 0 * * *"
    assert initial.origins["orchestration.schedule"] == Origin.SYSTEM_ENRICHMENT.value
    assert initial.origins["targets.bronze.table.dataset"] == Origin.SYSTEM_ENRICHMENT.value
    assert initial.origins["converter.output.format"] == Origin.GENERIC_ENRICHMENT.value
    assert initial.origins["metadata.version"] == Origin.SCHEMA_DEFAULT.value

    state = forge.submit_values(
        session_id,
        {"orchestration.schedule": "0 6 * * *"},
        Origin.USER,
    )

    assert state.contract["orchestration"]["schedule"] == "0 6 * * *"
    assert state.origins["orchestration.schedule"] == Origin.USER.value
    assert state.candidate_issues == []
    schedule_write = next(
        applied
        for applied in reversed(state.applied)
        if applied.path == "orchestration.schedule"
    )
    assert schedule_write.origin == Origin.USER
    assert schedule_write.rule_id is None


def test_state_exposes_schema_descriptions_for_lower_origin_overrides_only():
    forge, session_id = start_rocket()
    initial = forge.get_state(session_id)
    overridable = {field.path: field for field in initial.overridable}

    schedule = overridable["orchestration.schedule"]
    assert schedule.current_value == "0 0 * * *"
    assert schedule.current_origin == Origin.SYSTEM_ENRICHMENT
    assert schedule.value_schema["pattern"] == r"^\S+(?:\s+\S+){4}$"
    assert "metadata.version" in overridable
    assert "converter.output.format" in overridable
    assert "metadata.sourceSystemGcpId" not in overridable

    updated = forge.submit_values(
        session_id,
        {"orchestration.schedule": "0 6 * * *"},
        Origin.USER,
    )

    assert "orchestration.schedule" not in {
        field.path for field in updated.overridable
    }


def test_generic_enrichment_cannot_replace_user_value():
    contract: dict = {}
    origins: dict[str, Origin] = {}

    user_write = write_value(contract, origins, "value", "user", Origin.USER)
    generic_write = write_value(
        contract,
        origins,
        "value",
        "generic",
        Origin.GENERIC_ENRICHMENT,
        rule_id="generic.value",
    )

    assert user_write is not None
    assert generic_write is None
    assert contract["value"] == "user"
    assert origins["value"] == Origin.USER


def test_system_enrichment_replaces_generic_enrichment():
    contract: dict = {}
    origins: dict[str, Origin] = {}

    write_value(
        contract,
        origins,
        "value",
        "generic",
        Origin.GENERIC_ENRICHMENT,
        rule_id="generic.value",
    )
    system_write = write_value(
        contract,
        origins,
        "value",
        "system",
        Origin.SYSTEM_ENRICHMENT,
        rule_id="system.value",
    )

    assert system_write is not None
    assert system_write.rule_id == "system.value"
    assert contract["value"] == "system"
    assert origins["value"] == Origin.SYSTEM_ENRICHMENT


def test_generic_enrichment_replaces_schema_default():
    contract: dict = {}
    origins: dict[str, Origin] = {}

    write_value(contract, origins, "value", "default", Origin.SCHEMA_DEFAULT)
    generic_write = write_value(
        contract,
        origins,
        "value",
        "generic",
        Origin.GENERIC_ENRICHMENT,
        rule_id="generic.value",
    )

    assert generic_write is not None
    assert contract["value"] == "generic"
    assert origins["value"] == Origin.GENERIC_ENRICHMENT


def test_user_can_correct_an_existing_user_value_without_message_recency_logic():
    forge, session_id = start_rocket()
    forge.submit_values(session_id, {"metadata.id": "customer_accounts_daily"}, Origin.USER)
    forge.submit_values(session_id, {"metadata.owner": "team_a"}, Origin.USER)

    state = forge.submit_values(session_id, {"metadata.owner": "team_b"}, Origin.USER)

    assert state.contract["metadata"]["owner"] == "team_b"
    assert state.origins["metadata.owner"] == Origin.USER.value
    assert state.candidate_issues == []


def test_invalid_user_override_keeps_current_value_and_reports_candidate_issue():
    forge, session_id = start_rocket()

    state = forge.submit_values(
        session_id,
        {"orchestration.schedule": "not-a-cron"},
        Origin.USER,
    )

    assert state.contract["orchestration"]["schedule"] == "0 0 * * *"
    assert state.origins["orchestration.schedule"] == Origin.SYSTEM_ENRICHMENT.value
    assert state.candidate_issues
    assert state.candidate_issues[0].path == "orchestration.schedule"
    assert state.candidate_issues[0].validator == "pattern"


def test_invalid_user_to_user_override_keeps_previous_user_value():
    forge, session_id = start_rocket()
    forge.submit_values(
        session_id,
        {"metadata.id": "customer_accounts_daily"},
        Origin.USER,
    )

    state = forge.submit_values(session_id, {"metadata.id": "x"}, Origin.USER)

    assert state.contract["metadata"]["id"] == "customer_accounts_daily"
    assert state.origins["metadata.id"] == Origin.USER.value
    assert state.candidate_issues[0].path == "metadata.id"
    assert state.candidate_issues[0].validator == "minLength"


def test_user_cannot_write_unknown_schema_path():
    forge, session_id = start_rocket()

    state = forge.submit_values(
        session_id,
        {"metadata.unknown": "value"},
        Origin.USER,
    )

    assert "unknown" not in state.contract["metadata"]
    assert state.candidate_issues[0].path == "metadata.unknown"
    assert state.candidate_issues[0].validator == "path"
