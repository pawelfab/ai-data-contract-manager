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


def test_candidate_policy_reports_rejections_without_changing_behavior() -> None:
    state = ContractState()
    policy = CandidatePolicy(confidence_threshold=0.70)
    low_confidence = MutationCandidate(
        action=CandidateAction.SET,
        path="/metadata/dataFileId",
        value="ignored",
        confidence=0.69,
    )
    absent_remove = MutationCandidate(action=CandidateAction.REMOVE, path="/metadata/missing")

    result = policy.evaluate(state, [low_confidence, absent_remove])

    assert result.commands == []
    assert [decision.disposition for decision in result.decisions] == ["rejected", "rejected"]
    assert "confidence" in result.decisions[0].reason
    assert "does not exist" in result.decisions[1].reason
