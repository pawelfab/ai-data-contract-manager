from uuid import uuid4
from adcm.application.draft_projector import DraftProjector
from adcm.domain.models import ResolvedValue, ValueOrigin


def rv(path, value):
    return ResolvedValue(
        path=path,
        value=value,
        selected_candidate_id=uuid4(),
        origin=ValueOrigin.USER_EXPLICIT,
    )


def test_projection_rejects_unauthorized_paths():
    resolved = {
        "source.system": rv("source.system", "SAP"),
        "llm.invented.path": rv("llm.invented.path", "bad"),
    }
    draft = DraftProjector().project(resolved, {"source.system"}, revision=1)
    assert draft.values == {"source.system": "SAP"}
