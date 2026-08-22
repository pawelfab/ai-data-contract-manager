import json
from pathlib import Path

from contract_forge.adapters.outbound.contract_json_v1.parser import ContractJsonV1Parser
from contract_forge.application.services.rule_engine import evaluate_rules


def load_sample():
    raw = json.loads((Path(__file__).parents[2] / "resources" / "contract.json").read_text(encoding="utf-8"))
    return ContractJsonV1Parser().parse(raw)


def test_unpack_enabled_requires_format():
    c = load_sample()
    doc = {"preparator": {"operations": {"unpack": {"enabled": True}}}}
    req, issues = evaluate_rules(c.rules, c.raw_schema, doc)
    assert any(r.path.endswith("/unpack/format") for r in req)
