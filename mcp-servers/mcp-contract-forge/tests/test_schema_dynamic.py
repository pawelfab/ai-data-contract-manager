import json
from copy import deepcopy
from pathlib import Path

from contract_forge.engine import ContractForge
from contract_forge.models import Origin

ROOT = Path(__file__).resolve().parents[1]


def test_input_mode_policy_lives_only_in_ux_rules():
    schema_text = (ROOT / "config" / "contract.json").read_text(encoding="utf-8")
    rules = json.loads((ROOT / "config" / "ux_rules_contract_v1.json").read_text(encoding="utf-8"))

    assert "x-acdm-input-mode" not in schema_text
    assert rules["workflow"]["input_modes"] == {
        "metadata.sourceSystemGcpId": "explicit",
        "source.sourceType": "explicit",
        "metadata.id": "explicit",
        "metadata.dataFieldId": "explicit",
    }


def test_new_required_metadata_field_is_discovered_without_adcm_code_change(tmp_path):
    schema = json.loads((ROOT / "config" / "contract.json").read_text(encoding="utf-8"))
    rules = json.loads((ROOT / "config" / "ux_rules_contract_v1.json").read_text(encoding="utf-8"))
    schema["$defs"]["Metadata"]["required"].append("businessDomain")
    schema["$defs"]["Metadata"]["properties"]["businessDomain"] = {
        "type": "string",
        "minLength": 2,
        "x-acdm-question": "Jaka jest domena biznesowa?"
    }

    forge = ContractForge(schema, rules, deploy_env="dev")
    state = forge.start_session()
    sid = state.session_id
    state = forge.submit_values(sid, {"metadata.sourceSystemGcpId": "sap"}, Origin.USER)
    assert any(r.path == "metadata.businessDomain" for r in state.pending)


def test_system_with_multiple_source_types_reveals_source_type_choice():
    schema = json.loads((ROOT / "config" / "contract.json").read_text(encoding="utf-8"))
    rules = json.loads((ROOT / "config" / "ux_rules_contract_v1.json").read_text(encoding="utf-8"))
    rules["systems"]["multi"] = {"source_types": ["csv", "json"], "rules": []}

    forge = ContractForge(schema, rules, deploy_env="dev")
    state = forge.start_session()
    state = forge.submit_values(
        state.session_id,
        {"metadata.sourceSystemGcpId": "multi"},
        Origin.USER,
    )
    assert state.pending[0].path == "source.sourceType"
    assert state.pending[0].input_mode == "explicit"
    assert state.pending[0].allowed_values == ["csv", "json"]

    state = forge.submit_values(
        state.session_id,
        {"source.sourceType": "json"},
        Origin.USER,
    )
    assert state.contract["source"]["sourceType"] == "json"
    assert state.pending[0].path == "metadata.id"


def test_future_data_field_id_uses_input_mode_from_ux_rules():
    schema = json.loads((ROOT / "config" / "contract.json").read_text(encoding="utf-8"))
    rules = json.loads((ROOT / "config" / "ux_rules_contract_v1.json").read_text(encoding="utf-8"))
    metadata = schema["$defs"]["Metadata"]
    metadata["required"].append("dataFieldId")
    metadata["properties"]["dataFieldId"] = {
        "type": "string",
        "minLength": 1,
        "x-acdm-question": "Jaki jest identyfikator pola danych?",
    }

    forge = ContractForge(schema, rules, deploy_env="dev")
    state = forge.start_session()
    state = forge.submit_values(
        state.session_id,
        {"metadata.sourceSystemGcpId": "sap"},
        Origin.USER,
    )
    data_field = next(r for r in state.pending if r.path == "metadata.dataFieldId")

    assert data_field.input_mode == "explicit"


def test_array_object_requirement_exposes_minimal_resolved_item_schema():
    forge = ContractForge.from_files(
        ROOT / "config" / "contract.json",
        ROOT / "config" / "ux_rules_contract_v1.json",
        deploy_env="dev",
    )
    state = forge.start_session()
    state = forge.submit_values(
        state.session_id,
        {"metadata.sourceSystemGcpId": "sap"},
        Origin.USER,
    )
    columns = next(requirement for requirement in state.pending if requirement.path == "source.columns")

    assert columns.value_schema["type"] == "array"
    assert columns.value_schema["items"]["type"] == "object"
    assert columns.value_schema["items"]["required"] == ["name", "dataType"]
    assert columns.value_schema["items"]["properties"]["name"]["type"] == "string"
    assert "DATE" in columns.value_schema["items"]["properties"]["dataType"]["enum"]

    rocket = forge.start_session()
    rocket = forge.submit_values(
        rocket.session_id,
        {"metadata.sourceSystemGcpId": "rocket"},
        Origin.USER,
    )
    fixed_columns = next(
        requirement
        for requirement in rocket.pending
        if requirement.path == "source.columns"
    )
    assert fixed_columns.value_schema["items"]["required"] == [
        "name",
        "start",
        "end",
        "dataType",
    ]
