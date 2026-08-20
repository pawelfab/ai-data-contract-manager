import json
from pathlib import Path

import pytest

from contract_forge.compiler import ContractDefinitionError, compile_contract
from contract_forge.contracts import InMemoryContractAdapter
from contract_forge.engine import ContractForge

ROOT = Path(__file__).resolve().parents[1]


def schema_with(rules, properties=None):
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "section": {
                "type": "object",
                "properties": properties or {"enabled": {"type": "boolean"}},
                "x-contract-rules": rules,
            }
        },
    }


def compile_problems(rules, properties=None):
    with pytest.raises(ContractDefinitionError) as excinfo:
        compile_contract(InMemoryContractAdapter(schema_with(rules, properties)))
    return excinfo.value.problems


def test_unknown_kind_is_a_configuration_error_not_an_invalid_session():
    problems = compile_problems(
        [{"id": "future.rule", "kind": "super_new_business_rule", "message": "..."}]
    )

    assert len(problems) == 1
    assert "unknown x-contract-rule kind 'super_new_business_rule'" in problems[0]


def test_unknown_operator_is_rejected_even_when_the_condition_is_not_active_yet():
    """A user must not walk fifteen turns before learning the contract is unusable."""
    problems = compile_problems(
        [
            {
                "id": "future.rule",
                "kind": "conditional_required",
                "condition": {"path": "enabled", "equals": True},
                "assertion": {"path": "spec", "someUnknownOperator": "x"},
                "message": "...",
            }
        ]
    )

    assert len(problems) == 1
    assert "assertion" in problems[0]
    assert "'someUnknownOperator'" in problems[0]


def test_unknown_operator_nested_in_any_of_is_found():
    problems = compile_problems(
        [
            {
                "id": "future.rule",
                "kind": "at_least_one",
                "assertion": {
                    "anyOf": [
                        {"path": "a", "exists": True},
                        {"path": "b", "matchesRegex": "^x"},
                    ]
                },
                "message": "...",
            }
        ]
    )

    assert len(problems) == 1
    assert "anyOf[1]" in problems[0]
    assert "'matchesRegex'" in problems[0]


def test_the_note_equals_typo_is_reported_rather_than_silently_aliased():
    problems = compile_problems(
        [
            {
                "id": "typo.rule",
                "kind": "conditional_forbidden",
                "condition": {"path": "enabled", "noteEquals": "fixed_width"},
                "assertion": {"path": "spec", "exists": False},
                "message": "...",
            }
        ]
    )

    assert len(problems) == 1
    assert "condition" in problems[0]
    assert "'noteEquals'" in problems[0]


def test_every_problem_is_collected_so_the_contract_can_be_repaired_in_one_pass():
    problems = compile_problems(
        [
            {"id": "a", "kind": "unknown_kind", "message": "..."},
            {"id": "b", "kind": "cross_field", "assertion": {"path": "x", "bogus": 1}, "message": "..."},
            {"id": "c", "kind": "cross_field", "assertion": {"path": "x"}, "message": "..."},
        ]
    )

    assert len(problems) == 3
    assert any("unknown x-contract-rule kind" in problem for problem in problems)
    assert any("'bogus'" in problem for problem in problems)
    assert any("no operator present" in problem for problem in problems)


def test_duplicate_rule_ids_are_rejected():
    problems = compile_problems(
        [
            {"id": "same", "kind": "cross_field", "assertion": {"path": "a", "exists": True}, "message": "..."},
            {"id": "same", "kind": "cross_field", "assertion": {"path": "b", "exists": True}, "message": "..."},
        ]
    )

    assert len(problems) == 1
    assert "duplicate x-contract-rule id 'same'" in problems[0]


def test_rules_in_unreachable_defs_are_validated_too():
    """Definition validation covers the document, not just what a contract instance reaches."""
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {"section": {"type": "object"}},
        "$defs": {
            "NotReferencedYet": {
                "type": "object",
                "x-contract-rules": [{"id": "orphan", "kind": "mystery_kind", "message": "..."}],
            }
        },
    }

    with pytest.raises(ContractDefinitionError) as excinfo:
        compile_contract(InMemoryContractAdapter(schema))

    assert "$defs/NotReferencedYet" in excinfo.value.problems[0]


def test_unresolvable_rule_path_is_a_warning_not_a_failure():
    compiled = compile_contract(
        InMemoryContractAdapter(
            schema_with(
                [
                    {
                        "id": "inert.rule",
                        "kind": "cross_field",
                        "path": "notInSchema",
                        "assertion": {"path": "notInSchema", "exists": True},
                        "message": "...",
                    }
                ]
            )
        )
    )

    assert "inert.rule" in compiled.rules_by_id
    assert [diagnostic.severity for diagnostic in compiled.diagnostics] == ["warning"]
    assert "stays inert" in compiled.diagnostics[0].message


def test_the_shipped_contract_compiles_and_only_warns_about_placeholder_defs():
    forge = ContractForge.from_files(
        ROOT / "config" / "contract.json",
        ROOT / "config" / "ux_rules_contract_v1.json",
    )

    assert forge.compiled.rules_by_id
    # Every remaining warning belongs to a $defs placeholder that no property references.
    placeholders = {"SilverTableConfig", "TransformedColumn", "RecordValidationConfig"}
    for diagnostic in forge.compiled.diagnostics:
        assert any(name in diagnostic.pointer for name in placeholders), diagnostic


def test_a_broken_contract_stops_the_forge_before_any_session_exists():
    schema = json.loads((ROOT / "config" / "contract.json").read_text(encoding="utf-8"))
    rules = json.loads((ROOT / "config" / "ux_rules_contract_v1.json").read_text(encoding="utf-8"))
    schema["$defs"]["UnpackConfig"]["x-contract-rules"].append(
        {"id": "future.rule", "kind": "super_new_business_rule", "message": "..."}
    )

    with pytest.raises(ContractDefinitionError):
        ContractForge(schema, rules, deploy_env="dev")
