from pathlib import Path

from contract_forge.bootstrap.container import build_container
from contract_forge.bootstrap.settings import Settings


def forge():
    root = Path(__file__).parents[2]
    return build_container(Settings(
        contract_path=str(root / "resources" / "contract.json"),
        enrichment_path=str(root / "resources" / "ux_rules.json"),
        discovery_path=str(root / "resources" / "discovery_rules.json"),
        discovery_strict=True,
    )).evaluate_contract


def test_empty_document_exposes_only_source_system_and_no_sap_leak():
    ev = forge().execute({})
    assert [r.path for r in ev.requirements] == ["/metadata/sourceSystemGcpId"]
    assert ev.suggestions == []
    assert ev.valid is False


def test_source_system_activates_global_copy_but_not_hidden_silver():
    ev = forge().execute({"metadata": {"sourceSystemGcpId": "sap"}})
    paths = {r.path for r in ev.requirements}
    assert "/metadata/id" in paths
    assert "/metadata/version" in paths
    values = {s.path: s.value for s in ev.suggestions}
    assert values["/metadata/id"] == "sap"
    assert "/silver/tables/0/table/dataset" not in values
    assert ev.valid is False


def test_structural_parents_are_not_exposed_after_source():
    ev = forge().execute({"metadata": {"sourceSystemGcpId": "sap"}})
    paths = {r.path for r in ev.requirements}
    assert "/metadata" not in paths
    assert "/orchestration" not in paths
