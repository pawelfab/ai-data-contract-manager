import json
from pathlib import Path

from contract_forge.adapters.outbound.contract_json_v1.parser import ContractJsonV1Parser
from contract_forge.application.services.schema_engine import evaluate_schema


def load_sample():
    raw = json.loads((Path(__file__).parents[2] / "resources" / "contract.json").read_text(encoding="utf-8"))
    return ContractJsonV1Parser().parse(raw)


BASE = {
    "metadata": {"id": "sap", "version": "1.0.0", "sourceSystemGcpId": "sap", "dataFileId": "sap_pipeline"},
    "orchestration": {"schedule": "@daily", "startDate": "2025-01-01"},
    "source": {
        "sourceType": "jdbc",
        "sourceTable": "CUSTOMER",
        "jdbcConnectionName": "SAP",
        "dataDanych": "2025-01-01",
        "systemZrodlowy": "sap",
        "sourceName": "CUSTOMER",
    },
}


def walk(document):
    c = load_sample()
    return evaluate_schema(c.raw_schema, c.defs, document)


def paths_for(document):
    req, _, _ = walk(document)
    return {r.path for r in req}


def test_empty_document_discovers_root_and_nested_required():
    c = load_sample()
    req, sug, issues = evaluate_schema(c.raw_schema, c.defs, {})
    paths = {r.path for r in req}
    # SchemaEngine remains formal and therefore still exposes structural parents.
    assert "/metadata" in paths
    assert "/metadata/id" in paths
    assert "/orchestration" in paths
    assert not issues


def test_enabled_silver_discovers_the_first_table():
    paths = paths_for({**BASE, "silver": {"enabled": True}})
    assert {
        "/silver/tables/0/table/project",
        "/silver/tables/0/table/dataset",
        "/silver/tables/0/table/table",
        "/silver/tables/0/source",
        "/silver/tables/0/pk",
        "/silver/tables/0/columns",
    } <= paths


def test_a_column_list_is_asked_for_as_a_whole():
    # columns has minItems but no expand annotation, so it stays one fillable array. Asking
    # for columns/0/name would capture the first column and silently drop the rest.
    paths = paths_for({**BASE, "silver": {"enabled": True}})
    assert "/silver/tables/0/columns" in paths
    assert not [p for p in paths if p.startswith("/silver/tables/0/columns/")]


def test_present_but_empty_array_is_a_cardinality_error():
    document = {**BASE, "silver": {"enabled": True, "tables": []}}
    req, _, issues = walk(document)
    violations = [i for i in issues if i.path == "/silver/tables"]
    assert violations and violations[0].severity == "error"
    assert "at least 1" in violations[0].message
    # The element requirements are still discovered, so the user can fill the table in.
    assert "/silver/tables/0/table/project" in {r.path for r in req}


def test_existing_elements_are_walked_without_synthesis():
    document = {
        **BASE,
        "silver": {"enabled": True, "tables": [{"table": {"project": "p", "dataset": "d", "table": "t"}}]},
    }
    req, _, issues = walk(document)
    paths = {r.path for r in req}
    assert "/silver/tables/0/source" in paths
    assert "/silver/tables/1/source" not in paths
    assert not [i for i in issues if i.path == "/silver/tables"]


def test_enabled_gold_discovers_the_first_entry():
    paths = paths_for({**BASE, "gold": {"enabled": True}})
    assert {
        "/gold/entries/0/table/project",
        "/gold/entries/0/table/dataset",
        "/gold/entries/0/table/table",
    } <= paths


def test_scalar_array_shorter_than_min_items_is_reported():
    # Synthesising over `items: {"type": "string"}` produces no requirements at all, so
    # without the cardinality check an empty list would pass as valid.
    document = {
        **BASE,
        "preparator": {"enabled": True, "input": {"files": []}},
    }
    _, _, issues = walk(document)
    assert [i for i in issues if i.path and i.path.endswith("/files")]


def test_a_required_array_is_never_expanded_on_its_own():
    schema = {
        "type": "object",
        "required": ["plain", "bounded", "flagged"],
        "properties": {
            "plain": {"type": "array", "items": {"$ref": "#/$defs/Item"}},
            # minItems without the annotation: cardinality only, still atomic.
            "bounded": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/Item"}},
            # the annotation is permission, minItems is the count — a flag alone expands nothing.
            "flagged": {
                "type": "array",
                "x-requirement-expand-items": True,
                "items": {"$ref": "#/$defs/Item"},
            },
        },
    }
    defs = {"Item": {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}}}
    req, _, _ = evaluate_schema(schema, defs, {})
    paths = {r.path for r in req}
    assert paths == {"/plain", "/bounded", "/flagged"}


def test_annotation_plus_min_items_expands_exactly_min_items():
    schema = {
        "type": "object",
        "required": ["rows"],
        "properties": {
            "rows": {
                "type": "array",
                "minItems": 2,
                "x-requirement-expand-items": True,
                "items": {"$ref": "#/$defs/Item"},
            }
        },
    }
    defs = {"Item": {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}}}
    req, _, _ = evaluate_schema(schema, defs, {})
    paths = {r.path for r in req}
    assert "/rows/0/name" in paths
    assert "/rows/1/name" in paths
    assert "/rows/2/name" not in paths
