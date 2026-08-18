import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).parents[1]
SCHEMA_PATH = REPOSITORY_ROOT / "contracts" / "data-contract.schema.json"
RULE_SOURCE_PATH = REPOSITORY_ROOT / "examples" / "contract-rules.json"
RULE_FIELDS = ("id", "kind", "message", "path")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_schema_includes_every_legacy_contract_rule_in_existing_style() -> None:
    schema = read_json(SCHEMA_PATH)
    rule_source = read_json(RULE_SOURCE_PATH)

    expected_rule_owners = rule_source["$defs"]
    definitions = schema["$defs"]

    for name, source_definition in expected_rule_owners.items():
        actual_rules = definitions[name]["x-contract-rules"]
        expected_rules = [
            {field: rule[field] for field in RULE_FIELDS}
            for rule in source_definition["x-contract-rules"]
        ]

        assert actual_rules == expected_rules

    rule_ids = [
        rule["id"]
        for definition in expected_rule_owners.values()
        for rule in definition["x-contract-rules"]
    ]
    assert len(rule_ids) == 12
    assert len(rule_ids) == len(set(rule_ids))
    assert "x-acdm-rule-catalog" not in json.dumps(schema)
    assert all(
        set(rule) == set(RULE_FIELDS)
        for definition in definitions.values()
        for rule in definition.get("x-contract-rules", [])
    )


def test_schema_and_active_examples_are_valid_json() -> None:
    read_json(SCHEMA_PATH)

    for example_path in (REPOSITORY_ROOT / "examples").glob("*.contract.json"):
        read_json(example_path)
