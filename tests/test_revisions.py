from adcm.application.turn_processor import TurnProcessor
from adcm.domain.models import (
    ChatMessage,
    ConversationState,
    CorrectionIntent,
    ExtractedSignal,
    TurnInterpretation,
    ValueCandidate,
    ValueOrigin,
)


def test_correction_supersedes_old_signal_and_keeps_revision():
    state = ConversationState()
    processor = TurnProcessor()
    processor.apply_user_turn(
        state,
        ChatMessage(role="user", content="system Oracle"),
        TurnInterpretation(extracted_signals=[ExtractedSignal(concept="source_system", value="Oracle")]),
    )
    initial_signal = state.signals[0]
    candidate = ValueCandidate(
        path="source.system",
        value="Oracle",
        origin=ValueOrigin.USER_EXPLICIT,
        evidence_ids=initial_signal.evidence_ids,
        source_signal_id=initial_signal.id,
        created_revision=state.revision,
        sequence=1,
    )
    state.value_candidates.append(candidate)
    processor.apply_user_turn(
        state,
        ChatMessage(role="user", content="jednak PostgreSQL"),
        TurnInterpretation(
            corrections=[CorrectionIntent(concept="source_system", previous_value="Oracle", new_value="PostgreSQL")]
        ),
    )
    assert state.signals[0].status == "superseded"
    assert state.signals[-1].value == "PostgreSQL"
    assert candidate.status == "superseded"
    assert candidate in state.value_candidates
    assert state.revision == 2
    assert state.revisions[-1].changes[0].old == "Oracle"
