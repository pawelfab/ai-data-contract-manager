from uuid import uuid4

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
    resolved = CandidateResolver().resolve([new, old])
    assert resolved["x"].value == "new"
