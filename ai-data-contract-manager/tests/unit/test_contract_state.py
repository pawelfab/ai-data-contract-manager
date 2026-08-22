from adcm.domain.contract.state import ContractState
from adcm.domain.contract.value import Authority, DerivedValue, Provenance


def test_user_overrides_derived_and_last_user_wins():
    state = ContractState()
    state.set_derived(DerivedValue(path="/x", value="default", source="default", priority=10))
    state.set_user("/x", "a", provenance=Provenance(source_type="chat"))
    state.set_user("/x", "b", provenance=Provenance(source_type="chat"))
    assert state.effective_document()["x"] == "b"


def test_array_pointer():
    state = ContractState()
    state.set_user(
        "/source/columns/0/name",
        "id",
        provenance=Provenance(source_type="chat"),
    )
    assert state.effective_document()["source"]["columns"][0]["name"] == "id"


def test_user_referenced_value_is_preserved_as_provenance():
    state = ContractState()
    state.set_user(
        "/silver/dataset",
        "ddd_dataset",
        authority=Authority.USER_REFERENCED,
        provenance=Provenance(source_type="jira", source_ref="JIRA-4323", evidence_id="e1"),
    )
    event = state.latest_user_values()["/silver/dataset"]
    assert event.authority == Authority.USER_REFERENCED
    assert event.provenance.source_ref == "JIRA-4323"


def test_set_pointer_reports_scalar_intermediate_conflict():
    from adcm.domain.contract.path import JsonPointerError, set_pointer

    try:
        set_pointer({"metadata": "bad"}, "/metadata/id", "x")
    except JsonPointerError as exc:
        assert "/metadata" in str(exc)
        assert "bad" in str(exc)
    else:
        raise AssertionError("expected JsonPointerError")
