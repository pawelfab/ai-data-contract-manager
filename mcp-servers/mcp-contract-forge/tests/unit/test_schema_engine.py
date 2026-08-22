import json
from pathlib import Path

from contract_forge.adapters.outbound.contract_json_v1.parser import ContractJsonV1Parser
from contract_forge.application.services.schema_engine import evaluate_schema


def load_sample():
    raw = json.loads((Path(__file__).parents[2] / "resources" / "contract.json").read_text(encoding="utf-8"))
    return ContractJsonV1Parser().parse(raw)


def test_empty_document_discovers_root_and_nested_required():
    c = load_sample()
    req, sug, issues = evaluate_schema(c.raw_schema, c.defs, {})
    paths = {r.path for r in req}
    # SchemaEngine remains formal and therefore still exposes structural parents.
    assert "/metadata" in paths
    assert "/metadata/id" in paths
    assert "/orchestration" in paths
    assert not issues
