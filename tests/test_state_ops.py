from __future__ import annotations

from acdm.models import ContractState, RequirementsCatalogue
from acdm.state_ops import (
    activate_scope,
    document_fingerprint,
    missing_required_paths,
    set_path,
    unresolved_optional_decisions,
)
from mcp_contract_forge import ContractSchemaService


def requirements(source: str, targets: list[str]) -> RequirementsCatalogue:
    payload = ContractSchemaService().get_onboarding_requirements(
        source, targets
    )
    return RequirementsCatalogue.model_validate(payload.model_dump(mode="json"))


def test_scope_activation_seeds_discriminator_and_targets() -> None:
    state = ContractState(conversation_id="conversation-1")

    activate_scope(state, requirements("csv", ["bronze", "silver"]))

    assert state.draft["source"]["sourceType"] == "csv"
    assert list(state.draft["targets"]) == ["bronze", "silver"]
    assert "metadata.id" in missing_required_paths(state)


def test_changing_scope_removes_inactive_branches() -> None:
    state = ContractState(conversation_id="conversation-1")
    activate_scope(
        state, requirements("fixed_width", ["bronze", "silver", "gold"])
    )
    set_path(state.draft, "source.uri", "file://source.dat")
    set_path(state.draft, "targets.gold.grain", ["customer_id"])

    activate_scope(state, requirements("csv", ["bronze"]))

    assert state.draft["source"] == {"sourceType": "csv"}
    assert list(state.draft["targets"]) == ["bronze"]


def test_document_fingerprint_is_stable_for_key_order() -> None:
    first = {"a": 1, "b": {"c": 2}}
    second = {"b": {"c": 2}, "a": 1}

    assert document_fingerprint(first) == document_fingerprint(second)


def test_skipped_optional_decision_is_remembered() -> None:
    state = ContractState(conversation_id="conversation-1")
    activate_scope(state, requirements("csv", ["bronze"]))
    assert any(
        item["path"] == "source.options"
        for item in unresolved_optional_decisions(state)
    )

    state.optional_decision_choices["source.options"] = False

    assert not any(
        item["path"] == "source.options"
        for item in unresolved_optional_decisions(state)
    )


def test_selected_optional_section_activates_conditional_requirements() -> None:
    state = ContractState(conversation_id="conversation-1")
    activate_scope(state, requirements("csv", ["bronze"]))

    state.optional_decision_choices["orchestration"] = True

    missing = missing_required_paths(state)
    assert "orchestration.dagId" in missing
    assert "orchestration.startDate" not in missing
