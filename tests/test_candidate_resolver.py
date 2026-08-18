from adcm.application.candidate_resolver import CandidateResolver
from adcm.domain.models import ValueCandidate, ValueOrigin


def test_user_beats_enrichment_and_default():
    candidates = [
        ValueCandidate(path="x", value="default", origin=ValueOrigin.MCP_DEFAULT),
        ValueCandidate(path="x", value="enriched", origin=ValueOrigin.MCP_ENRICHMENT),
        ValueCandidate(path="x", value="user", origin=ValueOrigin.USER_EXPLICIT),
    ]
    resolved = CandidateResolver().resolve(candidates)
    assert resolved["x"].value == "user"
    assert resolved["x"].origin == ValueOrigin.USER_EXPLICIT
