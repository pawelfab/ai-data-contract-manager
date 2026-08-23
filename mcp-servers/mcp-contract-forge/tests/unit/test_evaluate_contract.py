import json
from pathlib import Path

import pytest

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


def test_complete_sap_head_activates_bronze_first_and_holds_back_silver_and_gold():
    ev = forge().execute(COMPLETE_HEAD)
    values = {s.path: s.value for s in ev.suggestions}

    # Bronze is the first layer: Silver/Gold wait until Bronze itself is complete, so a user
    # sentence about Bronze cannot be matched against already-visible Silver paths.
    assert values["/bronzeTable"] == {}
    assert "/silver/enabled" not in values
    assert "/gold/enabled" not in values
    assert "/silver/tables/0/table/dataset" not in values
    # System rules keep their own trigger; only the layer chain changed.
    assert values["/converter/enabled"] is True
    assert values["/preparator/enabled"] is True


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


def bronze(system: str) -> dict:
    name = f"{system}_bronze"
    return {"table": {"project": name, "dataset": name, "table": name}, "columns": []}


def test_layer_names_follow_the_global_convention_once_silver_is_active():
    document = {**COMPLETE_HEAD, "bronzeTable": bronze("sap"), "silver": {"enabled": True}}
    values = {s.path: s.value for s in forge().execute(document).suggestions}
    # A global convention, not a per-system rule: no `silver_sap` special case survives.
    assert values["/silver/tables/0/table/dataset"] == "sap_silver"
    assert values["/silver/tables/0/source"] == "sap_bronze"


# --- Source -> Bronze -> Silver/Gold ------------------------------------------------------------
#
# The chain is driven by open formal requirements, so it must hold for every technical source
# type. These use a non-SAP system on purpose: SAP additionally activates Converter/Preparator,
# which is a separate concern verified further down.

SOURCES = {
    "jdbc": {
        "sourceType": "jdbc",
        "sourceTable": "CUSTOMER",
        "jdbcConnectionName": "ROCKET",
        "dataDanych": "2025-01-01",
        "systemZrodlowy": "rocket",
        "sourceName": "CUSTOMER",
    },
    "json": {"sourceType": "json", "dataDanych": "2025-01-01", "systemZrodlowy": "rocket"},
    "txt": {
        "sourceType": "txt",
        "dataDanych": "2025-01-01",
        "systemZrodlowy": "rocket",
        "encoding": "UTF-8",
    },
    "fixed_width": {
        "sourceType": "fixed_width",
        "dataDanych": "2025-01-01",
        "systemZrodlowy": "rocket",
        "fixedWidth": {"columns": [{"name": "a", "start": 1, "end": 5}]},
    },
}

SOURCE_TYPES = sorted(SOURCES)

ROCKET_HEAD = {
    "metadata": {
        "id": "rocket",
        "version": "1.0.0",
        "sourceSystemGcpId": "rocket",
        "dataFileId": "customer",
    },
    "orchestration": {"schedule": "@daily", "startDate": "2025-01-01"},
}

LAYERS = ("/bronzeTable", "/silver", "/gold")


def head(source_type: str, **sections) -> dict:
    return {**ROCKET_HEAD, "source": dict(SOURCES[source_type]), **sections}


def layer_values(evaluation) -> dict:
    return {
        s.path: s.value
        for s in evaluation.suggestions
        if s.path == "/bronzeTable" or s.path.startswith(tuple(f"{x}/" for x in LAYERS))
    }


def assert_bronze_scaffold_and_children_never_coexist(evaluation) -> None:
    """The scaffold `{}` must never be able to overwrite an already-filled Bronze.

    `/bronzeTable` requires `exists=false` and every child requires `exists=true`, so the two
    groups are mutually exclusive by construction rather than by suggestion ordering.
    """

    paths = {s.path for s in evaluation.suggestions}
    assert not (
        "/bronzeTable" in paths
        and any(path.startswith("/bronzeTable/") for path in paths)
    ), sorted(paths)


@pytest.mark.parametrize("source_type", SOURCE_TYPES)
def test_incomplete_source_activates_no_layer_at_all(source_type: str):
    ev = forge().execute(head(source_type, source={"sourceType": source_type}))
    assert layer_values(ev) == {}
    assert_bronze_scaffold_and_children_never_coexist(ev)


@pytest.mark.parametrize("source_type", SOURCE_TYPES)
def test_complete_source_activates_bronze_and_only_bronze(source_type: str):
    ev = forge().execute(head(source_type))
    assert layer_values(ev) == {"/bronzeTable": {}}
    assert_bronze_scaffold_and_children_never_coexist(ev)


@pytest.mark.parametrize("source_type", SOURCE_TYPES)
def test_an_activated_bronze_receives_its_global_names_and_an_empty_column_list(source_type: str):
    ev = forge().execute(head(source_type, bronzeTable={}))

    assert layer_values(ev) == {
        "/bronzeTable/table/project": "rocket_bronze",
        "/bronzeTable/table/dataset": "rocket_bronze",
        "/bronzeTable/table/table": "rocket_bronze",
        # Deliberately the whole array: a 1:1 flow declares no explicit column overrides.
        "/bronzeTable/columns": [],
    }
    assert_bronze_scaffold_and_children_never_coexist(ev)
    assert not [r.path for r in ev.requirements if r.path.startswith("/bronzeTable/columns/")]


@pytest.mark.parametrize("source_type", SOURCE_TYPES)
def test_only_a_complete_bronze_activates_silver_and_gold(source_type: str):
    incomplete = forge().execute(head(source_type, bronzeTable={"columns": []}))
    assert "/silver/enabled" not in layer_values(incomplete)
    assert "/gold/enabled" not in layer_values(incomplete)

    ev = forge().execute(head(source_type, bronzeTable=bronze("rocket")))
    values = layer_values(ev)
    assert values["/silver/enabled"] is True
    assert values["/gold/enabled"] is True
    # Still no deep values: the branches are not active in the document yet.
    assert "/silver/tables/0/table/project" not in values


@pytest.mark.parametrize("source_type", SOURCE_TYPES)
def test_active_layers_receive_globally_computed_identifiers(source_type: str):
    ev = forge().execute(
        head(
            source_type,
            bronzeTable=bronze("rocket"),
            silver={"enabled": True},
            gold={"enabled": True},
        )
    )
    values = layer_values(ev)

    assert values["/silver/tables/0/table/project"] == "rocket_silver"
    assert values["/silver/tables/0/table/dataset"] == "rocket_silver"
    assert values["/silver/tables/0/table/table"] == "rocket_silver"
    assert values["/gold/entries/0/table/project"] == "rocket_gold"
    assert values["/gold/entries/0/table/dataset"] == "rocket_gold"
    assert values["/gold/entries/0/table/table"] == "rocket_gold"
    # Silver reads the Bronze table produced above.
    assert values["/silver/tables/0/source"] == "rocket_bronze"


@pytest.mark.parametrize("source_type", SOURCE_TYPES)
def test_silver_primary_key_and_columns_stay_the_users_answer(source_type: str):
    ev = forge().execute(
        head(
            source_type,
            bronzeTable=bronze("rocket"),
            silver={"enabled": True},
            gold={"enabled": True},
        )
    )
    paths = {r.path for r in ev.requirements}
    values = layer_values(ev)

    # Both are open requirements that enrichment deliberately refuses to answer.
    assert {"/silver/tables/0/pk", "/silver/tables/0/columns"} <= paths
    assert "/silver/tables/0/pk" not in values
    assert "/silver/tables/0/columns" not in values
    # The identifiers are open requirements too, but enrichment already carries their answer,
    # so they stop being questions on the next evaluation.
    assert "/silver/tables/0/table/project" in values
    assert "/gold/entries/0/table/table" in values
    # The column list stays atomic — no invented column definitions.
    assert not [path for path in paths if path.startswith("/silver/tables/0/columns/")]


@pytest.mark.parametrize("source_type", SOURCE_TYPES)
def test_the_chain_reaches_a_fixed_point_in_ordered_phases(source_type: str):
    """Phase order matters more than the exact round count.

    This applies suggestions the crude way on purpose — it is a Forge-level convergence check,
    not a re-implementation of ADCM's `ValueResolver` semantics.
    """

    evaluate = forge().execute
    document = head(source_type)
    phases: list[str] = []

    for _ in range(10):
        evaluation = evaluate(document)
        assert_bronze_scaffold_and_children_never_coexist(evaluation)

        values = layer_values(evaluation)
        if "/silver/tables/0/table/project" in values:
            phase = "layer-names"
        elif "/silver/enabled" in values:
            phase = "layer-activation"
        elif "/bronzeTable/table/project" in values:
            phase = "bronze-values"
        elif "/bronzeTable" in values:
            phase = "bronze-scaffold"
        else:
            phase = "source"
        if not phases or phases[-1] != phase:
            phases.append(phase)

        applied = _apply(document, evaluation.suggestions)
        if applied == document:
            break
        document = applied
    else:
        raise AssertionError(f"no fixed point after 10 evaluations, phases={phases}")

    assert phases == ["bronze-scaffold", "bronze-values", "layer-activation", "layer-names"]
    assert {r.path for r in evaluate(document).requirements} == {
        "/silver/tables/0/pk",
        "/silver/tables/0/columns",
    }


@pytest.mark.parametrize("source_type", SOURCE_TYPES)
def test_changing_the_source_system_recomputes_every_derived_layer_name(source_type: str):
    document = head(source_type, bronzeTable=bronze("rocket"), silver={"enabled": True}, gold={"enabled": True})
    document["metadata"] = {**document["metadata"], "sourceSystemGcpId": "codas"}
    document["source"] = {**document["source"], "systemZrodlowy": "codas"}

    values = layer_values(forge().execute(document))

    assert values["/bronzeTable/table/table"] == "codas_bronze"
    assert values["/silver/tables/0/table/dataset"] == "codas_silver"
    assert values["/gold/entries/0/table/project"] == "codas_gold"
    assert not [value for value in values.values() if isinstance(value, str) and "rocket" in value]


def test_sap_keeps_its_system_rules_on_top_of_the_global_layer_convention():
    document = {
        **COMPLETE_HEAD,
        "bronzeTable": bronze("sap"),
        "silver": {"enabled": True},
        "gold": {"enabled": True},
        "preparator": {"enabled": True},
    }
    ev = forge().execute(document)
    values = {s.path: s.value for s in ev.suggestions}

    assert values["/bronzeTable/table/table"] == "sap_bronze"
    assert values["/silver/tables/0/table/dataset"] == "sap_silver"
    assert values["/gold/entries/0/table/table"] == "sap_gold"
    assert values["/converter/enabled"] is True
    assert values["/preparator/enabled"] is True
    assert "silver_sap" not in {v for v in values.values() if isinstance(v, str)}
    assert not [s for s in ev.suggestions if s.rule_id == "sap.silver_dataset"]
    # An active SAP Preparator still owes its operation; that defect is out of scope here.
    assert any(i.rule_id == "preparator.enabled_requires_operation" for i in ev.issues)


def _apply(document: dict, suggestions) -> dict:
    out = json.loads(json.dumps(document))
    for suggestion in sorted(suggestions, key=lambda x: -x.priority):
        parts = suggestion.path[1:].split("/")
        cursor = out
        for index, part in enumerate(parts[:-1]):
            container = [] if parts[index + 1].isdigit() else {}
            if isinstance(cursor, list):
                position = int(part)
                while len(cursor) <= position:
                    cursor.append(None)
                if cursor[position] is None:
                    cursor[position] = container
                cursor = cursor[position]
            else:
                if cursor.get(part) is None:
                    cursor[part] = container
                cursor = cursor[part]
        last = parts[-1]
        if isinstance(cursor, list):
            position = int(last)
            while len(cursor) <= position:
                cursor.append(None)
            cursor[position] = suggestion.value
        else:
            cursor[last] = suggestion.value
    return out
