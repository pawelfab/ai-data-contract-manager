from adcm.application.ports.forge import Requirement
from adcm.application.ports.llm import Candidate
from adcm.application.services.candidate_decision import CandidateDecisionStatus
from adcm.application.services.value_resolver import ValueResolver
from adcm.domain.contract.state import ContractState
from adcm.domain.contract.value import Authority, Provenance
from adcm.domain.evidence.models import EvidenceItem


def evidence(item_id="e", authority=Authority.USER_DIRECT):
    return [EvidenceItem(id=item_id, source_type="chat", authority=authority, content="value")]


def test_candidate_must_point_to_real_evidence():
    state = ContractState()
    outcome = ValueResolver().apply_candidates(
        state,
        [Candidate(path="/x", value="invented", evidence_id="missing")],
        [],
        [Requirement(path="/x", expectedType="string")],
    )
    assert outcome.changed is False
    assert outcome.decisions[0].reason == "unknown_evidence"
    assert state.latest_user_values() == {}


def test_jira_referenced_candidate_keeps_authority():
    state = ContractState()
    ev = [EvidenceItem(id="jira-1", source_type="jira", source_ref="JIRA-4323", authority=Authority.USER_REFERENCED, content="silver dataset ddd_dataset")]
    outcome = ValueResolver().apply_candidates(
        state,
        [Candidate(path="/silver/dataset", value="ddd_dataset", evidence_id="jira-1")],
        ev,
        [Requirement(path="/silver/dataset", expectedType="string")],
    )
    assert outcome.changed is True
    event = state.latest_user_values()["/silver/dataset"]
    assert event.authority == Authority.USER_REFERENCED


def test_structural_parent_scalar_is_rejected_without_mutation():
    state = ContractState()
    state.set_user("/silver/tables/0/table/project", "sap_project", provenance=Provenance(source_type="chat"))
    outcome = ValueResolver().apply_candidates(
        state,
        [Candidate(path="/silver/tables/0/table", value="sap_silver", evidence_id="e")],
        evidence(),
        [],
    )
    assert outcome.changed is False
    assert outcome.decisions[0].status == CandidateDecisionStatus.REJECTED
    assert outcome.decisions[0].reason == "destroys_container"
    assert state.effective_document()["silver"]["tables"][0]["table"]["project"] == "sap_project"


def test_invalid_type_rejected():
    outcome = ValueResolver().apply_candidates(
        ContractState(),
        [Candidate(path="/metadata/version", value=["1.0.0"], evidence_id="e")],
        evidence(),
        [Requirement(path="/metadata/version", expectedType="string")],
    )
    assert outcome.decisions[0].reason == "invalid_type"


def test_existing_field_can_be_edited_even_when_not_required():
    state = ContractState()
    state.set_user("/metadata/version", "1.0.0", provenance=Provenance(source_type="chat"))
    outcome = ValueResolver().apply_candidates(
        state,
        [Candidate(path="/metadata/version", value="1.1.0", evidence_id="e")],
        evidence(),
        [],
    )
    assert outcome.changed is True
    assert state.effective_document()["metadata"]["version"] == "1.1.0"


def test_lower_authority_candidate_is_shadowed():
    state = ContractState()
    state.set_user("/x", "direct", authority=Authority.USER_DIRECT, provenance=Provenance(source_type="chat"))
    outcome = ValueResolver().apply_candidates(
        state,
        [Candidate(path="/x", value="jira", evidence_id="j")],
        evidence("j", Authority.USER_REFERENCED),
        [],
    )
    assert outcome.changed is False
    assert outcome.decisions[0].status == CandidateDecisionStatus.SHADOWED
    assert state.effective_document()["x"] == "direct"


def test_same_accepted_value_is_not_progress():
    state = ContractState()
    state.set_user("/x", "same", provenance=Provenance(source_type="chat"))
    outcome = ValueResolver().apply_candidates(
        state,
        [Candidate(path="/x", value="same", evidence_id="e")],
        evidence(),
        [],
    )
    assert outcome.decisions[0].status == CandidateDecisionStatus.ACCEPTED
    assert outcome.changed is False


# Forge tells ADCM which values it will accept; ADCM checks membership and nothing else.
# The requirement below is deliberately anonymous — ADCM must not care what it selects.
CHOICE = [Requirement(path="/x", expectedType="string", allowedValues=["one", "two"])]


def test_value_outside_the_allowed_set_is_rejected():
    state = ContractState()
    outcome = ValueResolver().apply_candidates(
        state,
        [Candidate(path="/x", value="three", evidence_id="e")],
        evidence(),
        CHOICE,
    )
    assert outcome.decisions[0].status == CandidateDecisionStatus.REJECTED
    assert outcome.decisions[0].reason == "value_not_allowed"
    assert outcome.changed is False
    assert state.latest_user_values() == {}


def test_value_inside_the_allowed_set_is_accepted():
    state = ContractState()
    outcome = ValueResolver().apply_candidates(
        state,
        [Candidate(path="/x", value="two", evidence_id="e")],
        evidence(),
        CHOICE,
    )
    assert outcome.decisions[0].status == CandidateDecisionStatus.ACCEPTED
    assert state.effective_document()["x"] == "two"


def test_a_requirement_without_an_allowed_set_constrains_nothing():
    state = ContractState()
    outcome = ValueResolver().apply_candidates(
        state,
        [Candidate(path="/x", value="anything", evidence_id="e")],
        evidence(),
        [Requirement(path="/x", expectedType="string")],
    )
    assert outcome.decisions[0].status == CandidateDecisionStatus.ACCEPTED
