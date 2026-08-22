import json
from pathlib import Path

from contract_forge.adapters.outbound.contract_json_v1.parser import ContractJsonV1Parser


def load_sample():
    raw = json.loads((Path(__file__).parents[2] / "resources" / "contract.json").read_text(encoding="utf-8"))
    return ContractJsonV1Parser().parse(raw)


def test_contract_v1_normalizes_schema_rules_and_semantic_paths():
    c = load_sample()
    assert c.root.title == "IntegrationPipelineConfig"
    assert c.rules_spec_version == "1.0"
    assert c.semantic_paths.source_system == "/metadata/sourceSystemGcpId"
    assert any(r.id == "preparator.unpack.format_required_when_enabled" for r in c.rules)
    registry = [r for r in c.rules if r.id == "transformed_column.validations.registered"]
    assert registry and registry[0].capability == "unsupported"
