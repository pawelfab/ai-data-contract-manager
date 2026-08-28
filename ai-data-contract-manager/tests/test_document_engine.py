from adcm.application.candidate_policy import CandidatePolicy
from adcm.application.document_engine import DocumentEngine
from adcm.domain.contract import ContractState
from adcm.domain.mutations import CandidateAction, MutationCandidate
from adcm.domain.provenance import ValueSource


def test_user_change_is_history_and_latest_value_wins() -> None:
    state = ContractState()
    engine = DocumentEngine()
    policy = CandidatePolicy()

    first = MutationCandidate(action=CandidateAction.SET, path="/metadata/dataFileId", value="OLD")
    engine.apply(state, policy.decide(state, [first]))
    second = MutationCandidate(action=CandidateAction.SET, path="/metadata/dataFileId", value="NEW")
    engine.apply(state, policy.decide(state, [second]))

    assert state.document["metadata"]["dataFileId"] == "NEW"
    assert state.provenance["/metadata/dataFileId"].source == ValueSource.USER_EXPLICIT
    assert [event.new_value for event in state.mutation_log] == ["OLD", "NEW"]
