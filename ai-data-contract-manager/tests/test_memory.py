from adcm.models import (
    ConversationMemory,
    ExtractionMethod,
    PartialFact,
    UserFact,
)


def build_memory() -> ConversationMemory:
    return ConversationMemory(
        session_id="adcm-session",
        forge_session_id="forge-session",
    )


def test_newer_user_fact_replaces_older_fact_for_the_same_path():
    memory = build_memory()
    memory.remember_fact(
        UserFact(
            path="metadata.owner",
            value="team_a",
            message_sequence=1,
            extraction_method=ExtractionMethod.DETERMINISTIC,
        )
    )
    memory.remember_fact(
        UserFact(
            path="metadata.owner",
            value="team_b",
            message_sequence=5,
            extraction_method=ExtractionMethod.DETERMINISTIC,
        )
    )

    assert memory.get_fact("metadata.owner").value == "team_b"


def test_older_user_fact_does_not_replace_newer_fact():
    memory = build_memory()
    newer = UserFact(
        path="metadata.owner",
        value="team_b",
        message_sequence=5,
        extraction_method=ExtractionMethod.DETERMINISTIC,
    )
    older = UserFact(
        path="metadata.owner",
        value="team_a",
        message_sequence=1,
        extraction_method=ExtractionMethod.DETERMINISTIC,
    )

    assert memory.remember_fact(newer) is True
    assert memory.remember_fact(older) is False
    assert memory.get_fact("metadata.owner") == newer


def test_fact_with_equal_sequence_replaces_previous_fact():
    memory = build_memory()
    memory.remember_fact(
        UserFact(
            path="metadata.owner",
            value="team_a",
            message_sequence=5,
            extraction_method=ExtractionMethod.DETERMINISTIC,
        )
    )
    replacement = UserFact(
        path="metadata.owner",
        value="team_b",
        message_sequence=5,
        extraction_method=ExtractionMethod.DETERMINISTIC,
    )

    assert memory.remember_fact(replacement) is True
    assert memory.get_fact("metadata.owner") == replacement


def test_user_fact_carries_sequence_extraction_method_and_evidence():
    fact = UserFact(
        path="metadata.owner",
        value="team_b",
        message_sequence=5,
        extraction_method=ExtractionMethod.LLM,
        confidence=0.9,
        evidence="owner to team_b",
    )

    assert fact.path == "metadata.owner"
    assert fact.value == "team_b"
    assert fact.message_sequence == 5
    assert fact.extraction_method == ExtractionMethod.LLM
    assert fact.confidence == 0.9
    assert fact.evidence == "owner to team_b"


def test_user_message_sequence_is_monotonic_and_transcript_is_preserved():
    memory = build_memory()
    memory.add_assistant_message("Pierwsze pytanie")
    first_user = memory.add_user_message("owner team_a")
    memory.add_assistant_message("Drugie pytanie")
    second_user = memory.add_user_message("owner team_b")

    assert first_user.message_sequence == 1
    assert second_user.message_sequence == 2
    assert memory.next_message_sequence == 3
    assert [message.content for message in memory.messages] == [
        "Pierwsze pytanie",
        "owner team_a",
        "Drugie pytanie",
        "owner team_b",
    ]
    assert [message.message_sequence for message in memory.messages] == [None, 1, None, 2]


def test_partial_fact_is_replaced_by_newer_merge_and_can_be_cleared():
    memory = build_memory()
    memory.remember_partial(
        PartialFact(
            path="custom.fields",
            value=[{"name": "data_d"}],
            missing=["dataType"],
            message_sequence=1,
        )
    )
    newer = PartialFact(
        path="custom.fields",
        value=[{"name": "data_d", "dataType": "DATE"}],
        missing=[],
        message_sequence=2,
    )

    assert memory.remember_partial(newer) is True
    assert memory.get_partial("custom.fields") == newer

    memory.clear_partial("custom.fields")

    assert memory.get_partial("custom.fields") is None
