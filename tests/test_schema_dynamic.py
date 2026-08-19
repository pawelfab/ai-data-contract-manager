import json
from copy import deepcopy
from pathlib import Path

from contract_forge.engine import ContractForge
from contract_forge.models import Origin

ROOT = Path(__file__).resolve().parents[1]


def test_new_required_metadata_field_is_discovered_without_adcm_code_change(tmp_path):
    schema = json.loads((ROOT / "config" / "contract.json").read_text())
    rules = json.loads((ROOT / "config" / "ux_rules_contract_v1.json").read_text())
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
    schema = json.loads((ROOT / "config" / "contract.json").read_text())
    rules = json.loads((ROOT / "config" / "ux_rules_contract_v1.json").read_text())
    rules["systems"]["multi"] = {"source_types": ["csv", "json"], "rules": []}

    forge = ContractForge(schema, rules, deploy_env="dev")
    state = forge.start_session()
    state = forge.submit_values(
        state.session_id,
        {"metadata.sourceSystemGcpId": "multi"},
        Origin.USER,
    )
    assert state.pending[0].path == "source.sourceType"
    assert state.pending[0].allowed_values == ["csv", "json"]

    state = forge.submit_values(
        state.session_id,
        {"source.sourceType": "json"},
        Origin.USER,
    )
    assert state.contract["source"]["sourceType"] == "json"
    assert state.pending[0].path == "metadata.id"
