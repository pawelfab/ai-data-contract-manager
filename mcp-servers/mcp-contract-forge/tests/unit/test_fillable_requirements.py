from contract_forge.application.services.fillable_requirements import fillable_requirements
from contract_forge.domain.evaluation.models import Requirement


def test_structural_parent_drops_but_sibling_and_array_leaf_remain():
    req = [
        Requirement(path="/metadata", expectedType="object"),
        Requirement(path="/metadata/id", expectedType="string"),
        Requirement(path="/metadata/version", expectedType="string"),
        Requirement(path="/silver/tables/0/columns", expectedType="array"),
    ]
    paths = {r.path for r in fillable_requirements(req)}
    assert "/metadata" not in paths
    assert "/metadata/id" in paths
    assert "/metadata/version" in paths
    assert "/silver/tables/0/columns" in paths


def test_prefix_respects_segment_boundary_and_lonely_object_stays():
    req = [Requirement(path="/ab"), Requirement(path="/abc"), Requirement(path="/lonely", expectedType="object")]
    assert {r.path for r in fillable_requirements(req)} == {"/ab", "/abc", "/lonely"}
