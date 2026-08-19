import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, SchemaError


REPOSITORY_ROOT = Path(__file__).parents[1]
SCHEMA_PATH = REPOSITORY_ROOT / "contracts" / "contract.json"
RETIRED_SCHEMA_PATH = REPOSITORY_ROOT / "contracts" / "data-contract.schema.json"
RULE_SOURCE_PATH = REPOSITORY_ROOT / "examples" / "contract-rules.json"
RULE_FIELDS = ("id", "kind", "message", "path")
OWNER_APPROVED_ROOT_REQUIREMENTS = {"metadata", "source", "targets", "orchestration"}


class ArtifactFixtureError(ValueError):
    """A local migration/reference artifact cannot be read or does not match expectations."""


def read_json(path: Path) -> dict:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ArtifactFixtureError(f"Cannot read JSON fixture {path}: {error}") from error

    try:
        return json.loads(content)
    except json.JSONDecodeError as error:
        raise ArtifactFixtureError(
            f"Malformed JSON fixture {path}: {error.msg} "
            f"(line {error.lineno}, column {error.colno})"
        ) from error


def validate_owner_approved_schema_fixture(path: Path, schema: dict) -> None:
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise ArtifactFixtureError(f"Invalid JSON Schema fixture {path}: {error.message}") from error

    actual_requirements = set(schema.get("required", []))
    if actual_requirements != OWNER_APPROVED_ROOT_REQUIREMENTS:
        raise ArtifactFixtureError(
            f"Schema fixture mismatch {path}: expected root required fields "
            f"{sorted(OWNER_APPROVED_ROOT_REQUIREMENTS)!r}, got {sorted(actual_requirements)!r}"
        )


def local_definition_references(value: object) -> set[str]:
    if isinstance(value, dict):
        references = {
            reference.removeprefix("#/$defs/")
            for reference in [value.get("$ref")]
            if isinstance(reference, str) and reference.startswith("#/$defs/")
        }
        for item in value.values():
            references.update(local_definition_references(item))
        return references
    if isinstance(value, list):
        return set().union(*(local_definition_references(item) for item in value))
    return set()


def reachable_definition_names(schema: dict) -> set[str]:
    root_schema = {key: value for key, value in schema.items() if key != "$defs"}
    definitions = schema["$defs"]
    reachable: set[str] = set()
    pending = list(local_definition_references(root_schema))

    while pending:
        definition_name = pending.pop()
        if definition_name in reachable:
            continue
        reachable.add(definition_name)
        pending.extend(local_definition_references(definitions[definition_name]))

    return reachable


def contract_rules(document: dict) -> list[tuple[str, dict]]:
    return [
        (definition_name, rule)
        for definition_name, definition in document["$defs"].items()
        for rule in definition.get("x-contract-rules", [])
    ]


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


def test_schema_artifact_inventory_records_root_reachability_and_rule_gap() -> None:
    schema = read_json(SCHEMA_PATH)
    legacy_catalog = read_json(RULE_SOURCE_PATH)
    reachable_definitions = reachable_definition_names(schema)
    schema_rules = contract_rules(schema)
    legacy_rules = contract_rules(legacy_catalog)

    assert set(schema["required"]) == OWNER_APPROVED_ROOT_REQUIREMENTS
    assert len(reachable_definitions) == 33
    assert {"ConverterConfig", "PreparatorConfig"} <= reachable_definitions
    assert set(schema["$defs"]) - reachable_definitions == {
        "RecordValidationConfig",
        "SilverTableConfig",
        "TransformedColumn",
    }
    assert len(schema_rules) == 14
    assert len(legacy_rules) == 12
    assert {rule["id"] for _, rule in schema_rules} - {
        rule["id"] for _, rule in legacy_rules
    } == {"targets.bronze.required", "targets.gold.requires_silver"}
    assert {
        definition_name for definition_name, _ in schema_rules if definition_name not in reachable_definitions
    } == {"RecordValidationConfig", "SilverTableConfig", "TransformedColumn"}


def test_schema_and_active_examples_are_valid_json() -> None:
    schema = read_json(SCHEMA_PATH)
    validate_owner_approved_schema_fixture(SCHEMA_PATH, schema)
    assert set(schema["properties"]) >= {
        "metadata",
        "source",
        "converter",
        "preparator",
        "targets",
        "orchestration",
    }

    for example_path in (REPOSITORY_ROOT / "examples").glob("*.contract.json"):
        read_json(example_path)


def test_missing_or_retired_schema_fixture_fails_explicitly(tmp_path: Path) -> None:
    missing_schema_path = tmp_path / "missing.contract.json"

    with pytest.raises(ArtifactFixtureError) as error:
        read_json(missing_schema_path)

    assert str(missing_schema_path) in str(error.value)
    assert "Cannot read JSON fixture" in str(error.value)
    assert SCHEMA_PATH.name == "contract.json"
    assert not RETIRED_SCHEMA_PATH.exists()


def test_malformed_schema_fixture_identifies_its_path_and_reason(tmp_path: Path) -> None:
    malformed_schema_path = tmp_path / "malformed.contract.json"
    malformed_schema_path.write_text('{"type": ', encoding="utf-8")

    with pytest.raises(ArtifactFixtureError) as error:
        read_json(malformed_schema_path)

    assert str(malformed_schema_path) in str(error.value)
    assert "Malformed JSON fixture" in str(error.value)
    assert "line 1, column" in str(error.value)


def test_owner_approved_schema_mismatch_identifies_its_path_and_reason(tmp_path: Path) -> None:
    mismatched_schema_path = tmp_path / "mismatched.contract.json"
    mismatched_schema_path.write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "required": ["metadata", "source", "targets"],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ArtifactFixtureError) as error:
        validate_owner_approved_schema_fixture(
            mismatched_schema_path,
            read_json(mismatched_schema_path),
        )

    assert str(mismatched_schema_path) in str(error.value)
    assert "Schema fixture mismatch" in str(error.value)
    assert "orchestration" in str(error.value)
