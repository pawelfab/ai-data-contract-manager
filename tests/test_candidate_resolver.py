from uuid import uuid4

import pytest
from pydantic import ValidationError

from adcm.application.candidate_resolver import CandidateResolver
from adcm.domain.models import CandidateScope, ValueCandidate, ValueOrigin


def test_user_beats_enrichment_and_default():
    ev = [uuid4()]
    candidates = [
        ValueCandidate(path="x", value="default", origin=ValueOrigin.MCP_DEFAULT),
        ValueCandidate(path="x", value="enriched", origin=ValueOrigin.MCP_ENRICHMENT),
        ValueCandidate(path="x", value="user", origin=ValueOrigin.USER_EXPLICIT, evidence_ids=ev),
    ]
    resolved = CandidateResolver().resolve(candidates)
    assert resolved["x"].value == "user"
    assert resolved["x"].origin == ValueOrigin.USER_EXPLICIT


def test_user_origin_beats_forge_rule_priority():
    evidence_ids = [uuid4()]
    candidates = [
        ValueCandidate(
            path="x",
            value="enriched",
            origin=ValueOrigin.MCP_ENRICHMENT,
            priority=999,
        ),
        ValueCandidate(
            path="x",
            value="user",
            origin=ValueOrigin.USER_EXPLICIT,
            evidence_ids=evidence_ids,
            priority=1,
        ),
    ]

    assert CandidateResolver().resolve(candidates)["x"].value == "user"


def test_system_enrichment_beats_generic_and_scope_stays_on_candidate():
    candidates = [
        ValueCandidate(
            path="x",
            value="generic",
            origin=ValueOrigin.MCP_ENRICHMENT,
            scope=CandidateScope.GENERIC,
            priority=50,
        ),
        ValueCandidate(
            path="x",
            value="system",
            origin=ValueOrigin.MCP_ENRICHMENT,
            scope=CandidateScope.SYSTEM,
            priority=60,
        ),
    ]
    resolved = CandidateResolver().resolve(candidates)
    winner = next(c for c in candidates if c.id == resolved["x"].selected_candidate_id)
    assert resolved["x"].value == "system"
    assert winner.scope == CandidateScope.SYSTEM
    assert not hasattr(resolved["x"], "scope")


def test_same_origin_correction_uses_revision_and_sequence_not_uuid():
    ev = [uuid4()]
    old = ValueCandidate(
        path="x",
        value="old",
        origin=ValueOrigin.USER_EXPLICIT,
        evidence_ids=ev,
        created_revision=1,
        sequence=1,
    )
    new = ValueCandidate(
        path="x",
        value="new",
        origin=ValueOrigin.USER_EXPLICIT,
        evidence_ids=ev,
        created_revision=2,
        sequence=2,
    )
    resolver = CandidateResolver()
    assert resolver.resolve([new, old])["x"].value == "new"

    regenerated = [
        old.model_copy(update={"id": uuid4()}),
        new.model_copy(update={"id": uuid4()}),
    ]
    assert resolver.resolve(regenerated)["x"].value == "new"


def test_confidence_is_the_final_policy_tie_breaker():
    first = ValueCandidate(
        path="x",
        value="alpha",
        origin=ValueOrigin.USER_EXPLICIT,
        evidence_ids=[uuid4()],
        created_revision=1,
        sequence=1,
        confidence=0.8,
        scope=CandidateScope.USER,
        rule_id="rule.alpha",
        reason="first descriptive reason",
    )
    second = ValueCandidate(
        path="x",
        value="omega",
        origin=ValueOrigin.USER_EXPLICIT,
        evidence_ids=[uuid4()],
        created_revision=1,
        sequence=1,
        confidence=0.8,
        scope=CandidateScope.GENERIC,
        rule_id="rule.omega",
        reason="second descriptive reason",
    )
    resolver = CandidateResolver()

    for candidates in ([first, second], [second, first]):
        with pytest.raises(ValueError, match="Ambiguous candidate rank"):
            resolver.resolve(candidates)


def test_equal_policy_rank_is_rejected_regardless_of_input_order():
    first = ValueCandidate(
        path="x",
        value="same",
        origin=ValueOrigin.USER_EXPLICIT,
        evidence_ids=[uuid4()],
        created_revision=1,
        sequence=1,
        reason="same semantic candidate",
    )
    second = ValueCandidate(
        path="x",
        value="same",
        origin=ValueOrigin.USER_EXPLICIT,
        evidence_ids=[uuid4()],
        created_revision=1,
        sequence=1,
        reason="same semantic candidate",
    )

    resolver = CandidateResolver()
    for candidates in ([first, second], [second, first]):
        with pytest.raises(ValueError, match="Ambiguous candidate rank"):
            resolver.resolve(candidates)


@pytest.mark.parametrize("confidence", [float("nan"), float("inf"), float("-inf")])
def test_value_candidate_rejects_non_finite_confidence(confidence):
    with pytest.raises(ValidationError):
        ValueCandidate(
            path="x",
            value="value",
            origin=ValueOrigin.MCP_DEFAULT,
            confidence=confidence,
        )


def test_resolver_rejects_non_finite_confidence_on_a_mutated_candidate():
    candidate = ValueCandidate(path="x", value="value", origin=ValueOrigin.MCP_DEFAULT)
    candidate.confidence = float("nan")

    with pytest.raises(ValueError, match="non-finite confidence"):
        CandidateResolver().resolve([candidate])


def test_resolver_rejects_duplicate_candidate_ids_before_updating_statuses():
    duplicate_id = uuid4()
    first = ValueCandidate(
        id=duplicate_id,
        path="x",
        value="default",
        origin=ValueOrigin.MCP_DEFAULT,
    )
    second = ValueCandidate(
        id=duplicate_id,
        path="x",
        value="enriched",
        origin=ValueOrigin.MCP_ENRICHMENT,
    )

    with pytest.raises(ValueError, match="Duplicate candidate ID"):
        CandidateResolver().resolve([first, second])

    assert first.status == "candidate"
    assert second.status == "candidate"


def test_non_finite_confidence_on_later_path_does_not_change_any_status():
    first_path_winner = ValueCandidate(
        path="a",
        value="enriched",
        origin=ValueOrigin.MCP_ENRICHMENT,
    )
    first_path_loser = ValueCandidate(
        path="a",
        value="default",
        origin=ValueOrigin.MCP_DEFAULT,
    )
    later_invalid = ValueCandidate(
        path="z",
        value="invalid",
        origin=ValueOrigin.MCP_DEFAULT,
    )
    later_invalid.confidence = float("nan")
    candidates = [first_path_winner, first_path_loser, later_invalid]

    with pytest.raises(ValueError, match="non-finite confidence"):
        CandidateResolver().resolve(candidates)

    assert [candidate.status for candidate in candidates] == [
        "candidate",
        "candidate",
        "candidate",
    ]


def test_policy_tie_on_later_path_does_not_change_any_status():
    first_path_winner = ValueCandidate(
        path="a",
        value="enriched",
        origin=ValueOrigin.MCP_ENRICHMENT,
    )
    first_path_loser = ValueCandidate(
        path="a",
        value="default",
        origin=ValueOrigin.MCP_DEFAULT,
    )
    later_tie_a = ValueCandidate(path="z", value="a", origin=ValueOrigin.MCP_DEFAULT)
    later_tie_b = ValueCandidate(path="z", value="b", origin=ValueOrigin.MCP_DEFAULT)
    candidates = [first_path_winner, first_path_loser, later_tie_a, later_tie_b]

    with pytest.raises(ValueError, match="Ambiguous candidate rank"):
        CandidateResolver().resolve(candidates)

    assert all(candidate.status == "candidate" for candidate in candidates)
