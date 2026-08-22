import json
from pathlib import Path

from contract_forge.adapters.outbound.contract_file.source import JsonFileContractSource
from contract_forge.adapters.outbound.contract_json_v1.parser import ContractJsonV1Parser


def test_source_and_parser_are_separate_boundaries(tmp_path: Path):
    path = tmp_path / "contract.json"
    path.write_text(
        json.dumps(
            {
                "title": "Example",
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
                "x-contract-rules-spec": {"version": "1.0"},
            }
        ),
        encoding="utf-8",
    )
    raw = JsonFileContractSource(path).load_raw()
    assert isinstance(raw, dict)
    normalized = ContractJsonV1Parser().parse(raw)
    assert normalized.root.title == "Example"
    assert normalized.rules_spec_version == "1.0"
