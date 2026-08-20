import json
from pathlib import Path

from contract_forge.compiler import compile_contract
from contract_forge.contract_rules import ContractRuleEngine
from contract_forge.contracts import InMemoryContractAdapter
from contract_forge.engine import ContractForge
from contract_forge.models import Origin

ROOT = Path(__file__).resolve().parents[1]


def engine_for(node_rules, node_schema=None):
    """Build a rule engine over a minimal schema carrying rules on ``section``."""
    section = {"type": "object", "properties": node_schema or {}}
    if node_rules is not None:
        section["x-contract-rules"] = node_rules
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {"section": section},
    }
    return ContractRuleEngine(compile_contract(InMemoryContractAdapter(schema)))


def test_conditional_required_becomes_a_missing_requirement_with_provenance():
    engine = engine_for(
        [
            {
                "id": "unpack.format_required",
                "kind": "conditional_required",
                "path": "format",
                "condition": {"path": "enabled", "equals": True},
                "assertion": {"path": "format", "exists": True},
                "message": "format is required when enabled is true.",
            }
        ],
        {"enabled": {"type": "boolean"}, "format": {"type": "string", "enum": ["zip", "gzip"]}},
    )

    contract = {"section": {"enabled": True}}
    issues = engine.evaluate(contract)

    assert [(issue.rule_id, issue.status, issue.path) for issue in issues] == [
        ("unpack.format_required", "missing", "section.format")
    ]

    requirement = engine.missing_requirements(contract, issues)[0]
    assert requirement.path == "section.format"
    assert requirement.status == "missing"
    assert requirement.reason == "contract_rule"
    assert requirement.rule_id == "unpack.format_required"
    assert requirement.message == "format is required when enabled is true."
    assert requirement.allowed_values == ["zip", "gzip"]
    # A missing value is not a blocking error: ADCM is expected to go and fetch it.
    assert engine.blocking_issues(issues) == []


def test_condition_that_does_not_match_keeps_the_rule_silent():
    engine = engine_for(
        [
            {
                "id": "unpack.format_required",
                "kind": "conditional_required",
                "path": "format",
                "condition": {"path": "enabled", "equals": True},
                "assertion": {"path": "format", "exists": True},
                "message": "format is required when enabled is true.",
            }
        ],
        {"enabled": {"type": "boolean"}, "format": {"type": "string"}},
    )

    assert engine.evaluate({"section": {"enabled": False}}) == []
    assert engine.evaluate({"section": {}}) == []


def test_conditional_forbidden_blocks_completion():
    engine = engine_for(
        [
            {
                "id": "spec.forbidden_when_disabled",
                "kind": "conditional_forbidden",
                "path": "spec",
                "condition": {"path": "enabled", "equals": False},
                "assertion": {"path": "spec", "exists": False},
                "message": "spec is not allowed when enabled is false.",
            }
        ],
        {"enabled": {"type": "boolean"}, "spec": {"type": "object"}},
    )

    issues = engine.evaluate({"section": {"enabled": False, "spec": {"key": "value"}}})

    assert [(issue.status, issue.path) for issue in issues] == [("forbidden", "section.spec")]
    assert [issue.rule_id for issue in engine.blocking_issues(issues)] == [
        "spec.forbidden_when_disabled"
    ]


def test_at_least_one_uses_any_of_and_reports_missing():
    engine = engine_for(
        [
            {
                "id": "output.at_least_one",
                "kind": "at_least_one",
                "path": "primary",
                "assertion": {
                    "anyOf": [
                        {"path": "primary", "notEquals": None},
                        {"path": "secondary", "notEquals": None},
                    ]
                },
                "message": "primary or secondary must be set.",
            }
        ],
        {"primary": {"type": "string"}, "secondary": {"type": "string"}},
    )

    assert engine.evaluate({"section": {"secondary": "value"}}) == []
    issues = engine.evaluate({"section": {}})
    assert [(issue.status, issue.path) for issue in issues] == [("missing", "section.primary")]


def test_cross_field_comparison_uses_gt_path():
    engine = engine_for(
        [
            {
                "id": "range.end_after_start",
                "kind": "cross_field",
                "path": "end",
                "assertion": {"path": "end", "gtPath": "start"},
                "message": "end must be greater than start.",
            }
        ],
        {"start": {"type": "integer"}, "end": {"type": "integer"}},
    )

    assert engine.evaluate({"section": {"start": 0, "end": 8}}) == []
    # Half-open ranges make an equal pair invalid, unlike the looser gtePath.
    assert [issue.status for issue in engine.evaluate({"section": {"start": 8, "end": 8}})] == ["invalid"]
    assert [issue.status for issue in engine.evaluate({"section": {"start": 10, "end": 4}})] == ["invalid"]
    # An incomplete pair is left to ordinary required discovery.
    assert engine.evaluate({"section": {"start": 10}}) == []


def test_computed_consistency_evaluates_a_formula():
    engine = engine_for(
        [
            {
                "id": "range.length_matches",
                "kind": "computed_consistency",
                "path": "length",
                "assertion": {"formula": "end - start", "equalsPath": "length"},
                "message": "length must equal end - start.",
            }
        ],
        {
            "start": {"type": "integer"},
            "end": {"type": "integer"},
            "length": {"type": "integer"},
        },
    )

    assert engine.evaluate({"section": {"start": 2, "end": 10, "length": 8}}) == []
    assert [issue.status for issue in engine.evaluate({"section": {"start": 2, "end": 10, "length": 9}})] == [
        "invalid"
    ]
    # No autofill operator exists in the DSL, so an absent target is not a violation.
    assert engine.evaluate({"section": {"start": 2, "end": 10}}) == []


def test_reference_integrity_and_not_in_walk_wildcards():
    engine = engine_for(
        [
            {
                "id": "keys.reference_existing_columns",
                "kind": "reference_integrity",
                "path": "keyColumns",
                "assertion": {"path": "keyColumns[*]", "existsIn": "columns[*].name"},
                "message": "keyColumns must reference existing columns.",
            },
            {
                "id": "keys.name_not_conflicting",
                "kind": "cross_field",
                "path": "keyName",
                "assertion": {"path": "keyName", "notIn": "columns[*].name"},
                "message": "keyName must differ from existing column names.",
            },
        ],
        {
            "columns": {"type": "array", "items": {"type": "object", "properties": {"name": {"type": "string"}}}},
            "keyColumns": {"type": "array", "items": {"type": "string"}},
            "keyName": {"type": "string"},
        },
    )

    valid = {"section": {"columns": [{"name": "a"}, {"name": "b"}], "keyColumns": ["a"], "keyName": "hash"}}
    assert engine.evaluate(valid) == []

    broken = {"section": {"columns": [{"name": "a"}], "keyColumns": ["missing"], "keyName": "a"}}
    assert sorted((issue.rule_id, issue.status) for issue in engine.evaluate(broken)) == [
        ("keys.name_not_conflicting", "invalid"),
        ("keys.reference_existing_columns", "invalid"),
    ]


def test_rule_without_assertion_is_skipped_and_never_blocks():
    engine = engine_for(
        [
            {
                "id": "record_validation.macro.registered",
                "kind": "registry_lookup",
                "path": "macro",
                "message": "macro must exist in VALIDATION_REGISTRY.",
            }
        ],
        {"macro": {"type": "string"}},
    )

    issues = engine.evaluate({"section": {"macro": "anything"}})

    assert [(issue.rule_id, issue.status) for issue in issues] == [
        ("record_validation.macro.registered", "skipped_non_executable")
    ]
    # The registry name lives only in `message`, which Forge must not parse.
    assert "not machine-readable" in issues[0].detail
    assert engine.blocking_issues(issues) == []
    assert engine.missing_requirements({"section": {"macro": "anything"}}, issues) == []


def test_missing_rule_target_outside_the_schema_is_skipped_not_pending():
    engine = engine_for(
        [
            {
                "id": "ghost.required",
                "kind": "conditional_required",
                "path": "ghost",
                "condition": {"path": "enabled", "equals": True},
                "assertion": {"path": "ghost", "exists": True},
                "message": "ghost is required.",
            }
        ],
        {"enabled": {"type": "boolean"}},
    )

    contract = {"section": {"enabled": True}}
    issues = engine.evaluate(contract)

    assert [(issue.rule_id, issue.status) for issue in issues] == [
        ("ghost.required", "skipped_non_executable")
    ]
    assert "not present in the active contract schema" in issues[0].detail
    assert engine.missing_requirements(contract, issues) == []


def test_rules_bind_per_array_item():
    engine = engine_for(
        None,
        {
            "columns": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"start": {"type": "integer"}, "end": {"type": "integer"}},
                    "x-contract-rules": [
                        {
                            "id": "column.end_after_start",
                            "kind": "cross_field",
                            "path": "end",
                            "assertion": {"path": "end", "gtPath": "start"},
                            "message": "end must be greater than start.",
                        }
                    ],
                },
            }
        },
    )

    contract = {"section": {"columns": [{"start": 0, "end": 8}, {"start": 9, "end": 3}]}}

    assert [issue.path for issue in engine.evaluate(contract)] == ["section.columns.1.end"]


def test_real_contract_rules_drive_the_forge_session_state():
    """The shipped contract must actually execute its preparator rules."""
    rules = json.loads((ROOT / "config" / "ux_rules_contract_v1.json").read_text(encoding="utf-8"))
    forge = ContractForge.from_files(ROOT / "config" / "contract.json", ROOT / "config" / "ux_rules_contract_v1.json")
    assert rules["version"]

    session = forge.start_session()
    sid = session.session_id
    forge.submit_values(sid, {"metadata.sourceSystemGcpId": "rocket"}, Origin.USER)

    # Optional sections are not reachable through submit_values, so exercise the rule
    # engine against the canonical contract the session already built.
    contract = forge.sessions[sid].contract
    contract["preparator"] = {"enabled": True, "operations": {"unpack": {"enabled": True}}}
    state = forge.get_state(sid)

    unpack_format = next(
        requirement
        for requirement in state.pending
        if requirement.path == "preparator.operations.unpack.format"
    )
    assert unpack_format.reason == "contract_rule"
    assert unpack_format.rule_id == "preparator.unpack.format_required_when_enabled"
    assert unpack_format.status == "missing"
    assert unpack_format.allowed_values == ["zip", "gzip", "bzip2", "tar", "tar.gz", "7z"]

    # Rules that are only prose are reported, but never block.
    skipped = {
        issue.rule_id
        for issue in state.contract_rule_issues
        if issue.status == "skipped_non_executable"
    }
    assert "targets.bronze.required" in skipped
