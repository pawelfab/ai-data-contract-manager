from adcm.application.document_engine import DocumentEngine
from adcm.application.proposal_reconciler import ProposalReconciler
from adcm.domain.contract import ContractState
from adcm.domain.mutations import MutationCommand, MutationOperation
from adcm.domain.proposals import Proposal
from adcm.domain.provenance import ValueSource


def test_explicit_user_value_beats_rule() -> None:
    state = ContractState()
    engine = DocumentEngine()
    engine.apply(state, [MutationCommand(operation=MutationOperation.ADD, path="/outputFilename", value="xxx.txt", source=ValueSource.USER_EXPLICIT)])

    proposal = Proposal(
        id="rule:file",
        path="/outputFilename",
        value="yyy.txt",
        source=ValueSource.APP_RULE,
        producer_id="rule.file",
    )
    commands, decisions = ProposalReconciler().reconcile(state, [proposal])
    assert commands == []
    assert state.document["outputFilename"] == "xxx.txt"
    assert decisions[0].action == "keep_current"


def test_stale_derived_value_is_removed() -> None:
    state = ContractState()
    engine = DocumentEngine()
    engine.apply(state, [MutationCommand(operation=MutationOperation.ADD, path="/derived", value="x", source=ValueSource.APP_RULE, producer_id="old.rule")])
    commands, _ = ProposalReconciler().reconcile(state, [])
    engine.apply(state, commands)
    assert "derived" not in state.document
