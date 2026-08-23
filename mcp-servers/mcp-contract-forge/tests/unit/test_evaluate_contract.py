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


COMPLETE_HEAD_NO_SOURCE = {
    "metadata": {"id": "sap", "version": "1.0.0", "sourceSystemGcpId": "sap", "dataFileId": "sap_pipeline"},
    "orchestration": {"schedule": "@daily", "startDate": "2025-01-01"},
}

COMPLETE_HEAD = {
    **COMPLETE_HEAD_NO_SOURCE,
    "source": {
        "sourceType": "jdbc",
        "sourceTable": "CUSTOMER",
        "jdbcConnectionName": "SAP",
        "dataDanych": "2025-01-01",
        "systemZrodlowy": "sap",
        "sourceName": "CUSTOMER",
    },
}


def test_enabling_silver_reveals_the_first_table_through_the_whole_pipeline():
    # Covers schema engine + fillable filter + discovery together: enabling the component is
    # enough, nothing has to materialise silver.tables[0] for its fields to be discovered.
    ev = forge().execute({**COMPLETE_HEAD, "silver": {"enabled": True}})
    paths = {r.path for r in ev.requirements}

    assert {
        "/silver/tables/0/table/project",
        "/silver/tables/0/table/table",
        "/silver/tables/0/source",
        "/silver/tables/0/pk",
        "/silver/tables/0/columns",
    } <= paths
    # The array itself is a structural parent once its element is expanded.
    assert "/silver/tables" not in paths
    # The column list stays atomic.
    assert not [p for p in paths if p.startswith("/silver/tables/0/columns/")]


def test_missing_discriminator_asks_only_for_the_source_type():
    ev = forge().execute({**COMPLETE_HEAD_NO_SOURCE, "source": {}})
    requirement = [r for r in ev.requirements if r.path == "/source/sourceType"]
    assert requirement, [r.path for r in ev.requirements]
    assert requirement[0].allowed_values == ["jdbc", "json", "txt", "fixed_width"]
    # Never a merge of requirements from every branch.
    assert not [r for r in ev.requirements if r.path.startswith("/source/") and r.path != "/source/sourceType"]


def test_invalid_discriminator_is_an_error_not_a_silent_pass():
    ev = forge().execute({**COMPLETE_HEAD_NO_SOURCE, "source": {"sourceType": "sap"}})
    assert ev.valid is False
    errors = [i for i in ev.issues if i.severity == "error" and i.path == "/source/sourceType"]
    assert errors and "jdbc" in errors[0].message


def test_a_chosen_branch_reveals_its_own_fields_only():
    ev = forge().execute({**COMPLETE_HEAD_NO_SOURCE, "source": {"sourceType": "jdbc"}})
    paths = {r.path for r in ev.requirements}
    assert {
        "/source/sourceTable",
        "/source/jdbcConnectionName",
        "/source/dataDanych",
        "/source/systemZrodlowy",
        "/source/sourceName",
    } <= paths
    # Fields belonging to the other branches must not leak in.
    assert "/source/encoding" not in paths
    assert "/source/fixedWidth" not in paths


def test_valid_is_not_the_signal_that_drives_the_conversation():
    # An in-progress contract is legitimately invalid while still having open questions.
    ev = forge().execute({**COMPLETE_HEAD_NO_SOURCE, "source": {"sourceType": "jdbc"}})
    assert ev.valid is False
    assert ev.requirements


def test_a_complete_document_is_valid():
    ev = forge().execute(COMPLETE_HEAD)
    assert ev.valid is True
    assert ev.requirements == []


def test_complete_sap_head_activates_optional_sections_without_materializing_deep_values():
    ev = forge().execute(COMPLETE_HEAD)
    values = {s.path: s.value for s in ev.suggestions}

    assert values["/silver/enabled"] is True
    assert values["/gold/enabled"] is True
    assert values["/converter/enabled"] is True
    assert values["/preparator/enabled"] is True
    assert "/silver/tables/0/table/dataset" not in values


def test_activated_sections_reveal_their_contract_requirements_on_the_next_evaluation():
    document = {
        **COMPLETE_HEAD,
        "silver": {"enabled": True},
        "gold": {"enabled": True},
        "converter": {"enabled": True},
        "preparator": {"enabled": True},
    }

    ev = forge().execute(document)
    paths = {r.path for r in ev.requirements}

    assert "/silver/tables/0/columns" in paths
    assert "/gold/entries/0/table/table" in paths
    assert any(i.path == "/preparator/operations" for i in ev.issues)


def test_dataset_enrichment_applies_once_the_silver_branch_is_visible():
    ev = forge().execute({**COMPLETE_HEAD, "silver": {"enabled": True}})
    values = {s.path: s.value for s in ev.suggestions}
    # The source system is known here, so system enrichment is legitimate.
    assert values["/silver/tables/0/table/dataset"] == "silver_sap"
