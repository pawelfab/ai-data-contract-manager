from uuid import uuid4

from adcm.application.draft_projector import DraftProjector
from adcm.domain.models import AllowedPath, CurrentSchemaView, ResolvedValue, ValueOrigin


def rv(path, value):
    return ResolvedValue(
        path=path,
        value=value,
        selected_candidate_id=uuid4(),
        origin=ValueOrigin.USER_EXPLICIT,
    )


def test_projection_rejects_unauthorized_paths_and_builds_nested_document():
    resolved = {
        "source.system": rv("source.system", "SAP"),
        "llm.invented.path": rv("llm.invented.path", "bad"),
    }
    view = CurrentSchemaView(
        schema_revision="v1",
        allowed_paths=[AllowedPath(path="source.system")],
    )
    draft = DraftProjector().project(resolved, view, revision=1)
    assert draft.values == {"source": {"system": "SAP"}}


def test_reprojection_removes_paths_no_longer_legal():
    resolved = {
        "source.format": rv("source.format", "parquet"),
        "source.delimited.delimiter": rv("source.delimited.delimiter", ";"),
    }
    parquet_view = CurrentSchemaView(
        schema_revision="v2",
        allowed_paths=[AllowedPath(path="source.format")],
    )
    draft = DraftProjector().project(resolved, parquet_view, revision=2)
    assert draft.values == {"source": {"format": "parquet"}}
