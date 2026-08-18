from adcm.application.turn_processor import TurnProcessor
from adcm.domain.models import (
    ChatMessage,
    ConversationState,
    CorrectionIntent,
    ExtractedSignal,
    TurnInterpretation,
)


def test_correction_supersedes_old_signal_and_keeps_revision():
    state = ConversationState()
    processor = TurnProcessor()
    processor.apply_user_turn(
        state,
        ChatMessage(role="user", content="system Oracle"),
        TurnInterpretation(extracted_signals=[ExtractedSignal(concept="source_system", value="Oracle")]),
    )
    processor.apply_user_turn(
        state,
        ChatMessage(role="user", content="jednak PostgreSQL"),
        TurnInterpretation(
            corrections=[CorrectionIntent(concept="source_system", previous_value="Oracle", new_value="PostgreSQL")]
        ),
    )
    assert state.signals[0].status == "superseded"
    assert state.signals[-1].value == "PostgreSQL"
    assert state.revision == 2
    assert state.revisions[-1].changes[0].old == "Oracle"
