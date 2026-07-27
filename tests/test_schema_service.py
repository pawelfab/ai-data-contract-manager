from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from mcp_contract_forge import ContractSchemaService

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def service() -> ContractSchemaService:
    return ContractSchemaService()


def load_example(name: str) -> dict:
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "name",
    [
        "csv-bronze.contract.json",
        "fixed-width-all-layers.contract.json",
    ],
)
def test_examples_are_valid(
    service: ContractSchemaService, name: str
) -> None:
    result = service.validate_contract(load_example(name))
    assert result.valid, result.issues


def test_csv_catalogue_contains_only_active_source(
    service: ContractSchemaService,
) -> None:
    catalogue = service.get_onboarding_requirements("csv", ["bronze"])
    paths = set(catalogue.allowed_paths)

    assert "source.uri" in catalogue.required_paths
    assert "source.columns" in catalogue.required_paths
    assert "metadata.version" in catalogue.required_paths
    assert "metadata.owner" in catalogue.required_paths
    assert "orchestration.dagId" in catalogue.required_paths
    assert "orchestration.schedule" in catalogue.required_paths
    assert "source.options.delimiter" in paths
    assert "targets.bronze.table.project" in catalogue.required_paths
    assert not any("recordLength" in path for path in paths)
    assert not any(path.startswith("targets.silver") for path in paths)
    assert any(
        decision.path == "source.options"
        for decision in catalogue.optional_decisions
    )
    assert not any(
        decision.path == "orchestration"
        for decision in catalogue.optional_decisions
    )


def test_fixed_width_catalogue_keeps_array_item_shape(
    service: ContractSchemaService,
) -> None:
    catalogue = service.get_onboarding_requirements(
        "fixed-width", ["bronze", "silver", "gold"]
    )
    columns = next(
        field for field in catalogue.field_catalog if field.path == "source.columns"
    )

    assert columns.item_required == ["name", "start", "end", "dataType"]
    assert columns.item_properties["start"]["type"] == "integer"
    assert columns.item_properties["end"]["minimum"] == 1
    assert "targets.gold.grain" in catalogue.required_paths


def test_common_fixed_width_typo_is_normalized(
    service: ContractSchemaService,
) -> None:
    catalogue = service.get_onboarding_requirements("fixed-with", ["bronze"])

    assert catalogue.source_type == "fixed_width"


@pytest.mark.parametrize(
    "layers",
    [
        ["silver"],
        ["bronze", "gold"],
        ["silver", "bronze"],
        ["bronze", "bronze"],
    ],
)
def test_invalid_target_sequence_is_rejected(
    service: ContractSchemaService, layers: list[str]
) -> None:
    with pytest.raises(ValueError):
        service.get_onboarding_requirements("csv", layers)


def test_fixed_width_overlap_is_reported(
    service: ContractSchemaService,
) -> None:
    contract = load_example("fixed-width-all-layers.contract.json")
    contract["source"]["columns"][1]["start"] = 7

    result = service.validate_contract(contract)

    assert not result.valid
    assert any(issue.code == "fixed_width.overlap" for issue in result.issues)


def test_gold_requires_silver(service: ContractSchemaService) -> None:
    contract = load_example("fixed-width-all-layers.contract.json")
    del contract["targets"]["silver"]

    result = service.validate_contract(contract)

    assert not result.valid
    assert any(
        issue.path == "targets.silver" and issue.code == "required"
        for issue in result.issues
    )


def test_invalid_source_path_is_reported(
    service: ContractSchemaService,
) -> None:
    contract = load_example("csv-bronze.contract.json")
    contract["targets"]["bronze"]["columns"][0][
        "sourcePath"
    ] = "source.columns.does_not_exist"

    result = service.validate_contract(contract)

    assert not result.valid
    assert any(
        issue.code == "target.unknown_source_column"
        for issue in result.issues
    )


def test_yaml_is_generated_only_for_valid_contract(
    service: ContractSchemaService,
) -> None:
    contract = load_example("csv-bronze.contract.json")

    result = service.generate_contract_yaml(contract)

    assert yaml.safe_load(result.yaml) == contract

    invalid = deepcopy(contract)
    del invalid["metadata"]["id"]
    with pytest.raises(ValueError):
        service.generate_contract_yaml(invalid)


def test_schedule_requires_five_field_linux_cron(
    service: ContractSchemaService,
) -> None:
    contract = load_example("csv-bronze.contract.json")
    contract["orchestration"] = {
        "dagId": "customers_pipeline",
        "schedule": "0 6 * *",
    }

    result = service.validate_contract(contract)

    issue = next(
        item
        for item in result.issues
        if item.path == "orchestration.schedule"
    )
    assert issue.code == "pattern"
    assert "Linux cron" in issue.description
    assert "pięcioma polami" in issue.description

    contract["orchestration"]["schedule"] = "0 6 * * *"
    assert service.validate_contract(contract).valid
