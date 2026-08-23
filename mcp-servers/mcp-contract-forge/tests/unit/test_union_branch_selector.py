import pytest

from contract_forge.adapters.outbound.contract_json_v1.parser import ContractJsonV1Parser
from contract_forge.application.services.schema_engine import evaluate_schema
from contract_forge.application.services.union_branch_selector import (
    BranchSelectionStatus,
    UnionBranchSelector,
)

DEFS = {
    "A": {
        "type": "object",
        "required": ["kind", "a"],
        "properties": {"kind": {"const": "a"}, "a": {"type": "string"}},
    },
    "B": {
        "type": "object",
        "required": ["kind", "b"],
        "properties": {"kind": {"const": "b"}, "b": {"type": "string"}},
    },
}

UNION = {
    "oneOf": [{"$ref": "#/$defs/A"}, {"$ref": "#/$defs/B"}],
    "x-discriminator": {"path": "kind"},
}


def select(document):
    return UnionBranchSelector().select(UNION, "/thing", document, DEFS)


def test_missing_discriminator_reports_the_allowed_values():
    selection = select({})
    assert selection.status is BranchSelectionStatus.MISSING_DISCRIMINATOR
    assert selection.discriminator_path == "/thing/kind"
    assert selection.allowed_values == ["a", "b"]
    assert selection.branch is None


def test_known_value_selects_exactly_one_branch():
    selection = select({"thing": {"kind": "b"}})
    assert selection.status is BranchSelectionStatus.SELECTED
    assert selection.branch == {"$ref": "#/$defs/B"}


def test_unknown_value_is_invalid_not_a_selection():
    selection = select({"thing": {"kind": "zzz"}})
    assert selection.status is BranchSelectionStatus.INVALID_DISCRIMINATOR
    assert selection.branch is None


def test_two_branches_claiming_one_value_are_ambiguous():
    defs = {"A": DEFS["A"], "B": {**DEFS["B"], "properties": {**DEFS["B"]["properties"], "kind": {"const": "a"}}}}
    selection = UnionBranchSelector().select(UNION, "/thing", {"thing": {"kind": "a"}}, defs)
    assert selection.status is BranchSelectionStatus.AMBIGUOUS


def test_a_union_without_an_annotation_is_not_selectable():
    assert UnionBranchSelector().selects({"oneOf": [{"$ref": "#/$defs/A"}]}) is False


def test_an_undiscriminated_union_stays_atomic():
    schema = {
        "type": "object",
        "required": ["thing"],
        "properties": {"thing": {"oneOf": [{"$ref": "#/$defs/A"}, {"$ref": "#/$defs/B"}]}},
    }
    req, _, _ = evaluate_schema(schema, DEFS, {})
    # The node itself is the requirement; no branch fields and no invented discriminator.
    assert [r.path for r in req] == ["/thing"]


def test_the_contract_linter_rejects_an_ambiguous_union():
    raw = {
        "type": "object",
        "properties": {
            "thing": {
                "oneOf": [{"$ref": "#/$defs/A"}, {"$ref": "#/$defs/B"}],
                "x-discriminator": {"path": "kind"},
            }
        },
        "$defs": {
            "A": DEFS["A"],
            "B": {**DEFS["B"], "properties": {**DEFS["B"]["properties"], "kind": {"const": "a"}}},
        },
    }
    with pytest.raises(ValueError, match="ambiguous|already claimed"):
        ContractJsonV1Parser().parse(raw)


def test_the_contract_linter_rejects_a_branch_without_discriminator_values():
    raw = {
        "type": "object",
        "properties": {
            "thing": {
                "oneOf": [{"$ref": "#/$defs/A"}, {"$ref": "#/$defs/Loose"}],
                "x-discriminator": {"path": "kind"},
            }
        },
        "$defs": {"A": DEFS["A"], "Loose": {"type": "object", "properties": {"kind": {"type": "string"}}}},
    }
    with pytest.raises(ValueError, match="no const/enum"):
        ContractJsonV1Parser().parse(raw)
