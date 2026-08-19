import pytest

from adcm.domain.contract_path import ContractPath


def test_write_pads_intermediate_list_of_objects_with_empty_objects():
    doc = {}
    ContractPath.write(doc, "silver.tables[2].source", "bronze.table")
    assert doc == {
        "silver": {
            "tables": [
                {},
                {},
                {"source": "bronze.table"},
            ]
        }
    }


def test_write_nested_arrays_and_read_back():
    doc = {}
    ContractPath.write(doc, "silver.tables[0].columns[1].name", "amount")
    assert ContractPath.read(doc, "silver.tables[0].columns[1].name") == "amount"


def test_write_nested_direct_arrays_and_read_back():
    document = {}

    ContractPath.write(document, "matrix[1][2].value", "x")

    assert document == {"matrix": [[], [{}, {}, {"value": "x"}]]}
    assert ContractPath.read(document, "matrix[1][2].value") == "x"


@pytest.mark.parametrize(
    "path",
    ["", ".silver", "silver.", "silver..tables", "silver[01]", "silver[*]", "[0].name"],
)
def test_parse_rejects_malformed_or_schema_wildcard_paths(path):
    with pytest.raises(ValueError):
        ContractPath.parse(path)


def test_write_rejects_incompatible_existing_container_shape():
    document = {"silver": []}

    with pytest.raises(TypeError):
        ContractPath.write(document, "silver.tables[0].name", "amount")
