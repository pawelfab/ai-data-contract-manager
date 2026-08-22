import json
from pathlib import Path

from contract_forge.adapters.outbound.contract_json_v1.source_linter import lint_source


def test_current_contract_has_no_dangling_refs():
    raw = json.loads((Path(__file__).parents[2] / "resources" / "contract.json").read_text(encoding="utf-8"))
    assert lint_source(raw) == []
