import pytest

from adcm.adapters.intent_heuristic import HeuristicIntentResolver
from adcm.application.intent_resolution_policy import IntentResolutionPolicy
from adcm.domain.mutations import CandidateAction, MutationCandidate
from adcm.domain.turn import IntentKind, IntentResolution


def candidate() -> MutationCandidate:
    return MutationCandidate(
        action=CandidateAction.SET,
        path="/converter/outputFilename",
        value="out.csv",
        evidence="test",
    )


@pytest.mark.parametrize(
    ("kind", "expected_candidates", "expected_query"),
    [
        (IntentKind.KNOWLEDGE, 0, "what options?"),
        (IntentKind.MUTATION, 1, None),
        (IntentKind.MIXED, 1, "what options?"),
        (IntentKind.UNRESOLVED, 0, None),
    ],
)
def test_policy_applies_intent_matrix(
    kind: IntentKind,
    expected_candidates: int,
    expected_query: str | None,
) -> None:
    raw = IntentResolution(
        intent_kind=kind,
        candidates=[candidate()],
        knowledge_query="what options?",
        unresolved=[{"value": "x"}],
    )

    effective = IntentResolutionPolicy().apply(raw)

    assert effective.intent_kind is kind
    assert len(effective.candidates) == expected_candidates
    assert effective.knowledge_query == expected_query
    if kind is IntentKind.UNRESOLVED:
        assert effective.unresolved == [
            {"value": "x"},
            {"reason": "intent could not be resolved"},
        ]
    else:
        assert effective.unresolved == raw.unresolved
    assert raw.candidates  # policy never mutates the raw result


@pytest.mark.asyncio
async def test_heuristic_distinguishes_knowledge_and_unresolved_fallback() -> None:
    resolver = HeuristicIntentResolver()
    knowledge = await resolver.resolve("jakie opcje converter dostepne?", document={})
    unknown = await resolver.resolve("opowiedz o projekcie", document={})

    assert knowledge.intent_kind is IntentKind.KNOWLEDGE
    assert knowledge.knowledge_query
    assert unknown.intent_kind is IntentKind.UNRESOLVED
    assert unknown.knowledge_query is None
    assert unknown.unresolved


@pytest.mark.parametrize("kind", [IntentKind.KNOWLEDGE, IntentKind.MIXED])
def test_policy_degrades_missing_knowledge_query_to_unresolved(kind: IntentKind) -> None:
    raw = IntentResolution(intent_kind=kind, candidates=[candidate()], knowledge_query="  ")
    effective = IntentResolutionPolicy().apply(raw)

    assert effective.intent_kind is IntentKind.UNRESOLVED
    assert effective.candidates == []
    assert effective.knowledge_query is None
    assert effective.unresolved == [{"reason": "knowledge_query is required for this intent kind"}]
    assert raw.knowledge_query == "  "
    assert raw.candidates


@pytest.mark.parametrize("invalid_reason", [None, "  ", {}, [], False, 0])
def test_policy_preserves_raw_unresolved_with_invalid_reason_and_adds_reason(
    invalid_reason: object,
) -> None:
    raw = IntentResolution(
        intent_kind=IntentKind.UNRESOLVED,
        unresolved=[{"reason": invalid_reason}],
    )
    effective = IntentResolutionPolicy().apply(raw)

    assert effective.intent_kind is IntentKind.UNRESOLVED
    assert effective.unresolved == [
        {"reason": invalid_reason},
        {"reason": "intent could not be resolved"},
    ]
    assert raw.unresolved == [{"reason": invalid_reason}]
