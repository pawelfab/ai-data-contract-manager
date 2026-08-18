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
