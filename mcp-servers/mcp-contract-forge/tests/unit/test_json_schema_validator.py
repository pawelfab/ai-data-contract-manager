import json
from pathlib import Path

from jsonschema import Draft202012Validator

from contract_forge.application.services.json_schema_validator import JsonSchemaValidator
from contract_forge.application.services.schema_validation_issue_mapper import map_schema_errors

RESOURCES = Path(__file__).parents[2] / "resources"

HEAD = {
    "metadata": {"id": "sap", "version": "1.0.0", "sourceSystemGcpId": "sap", "dataFileId": "sap_pipeline"},
    "orchestration": {"schedule": "@daily", "startDate": "2025-01-01"},
}
JDBC = {
    "sourceType": "jdbc",
    "sourceTable": "CUSTOMER",
    "jdbcConnectionName": "SAP",
    "dataDanych": "2025-01-01",
    "systemZrodlowy": "sap",
    "sourceName": "CUSTOMER",
}


def contract() -> dict:
    return json.loads((RESOURCES / "contract.json").read_text(encoding="utf-8"))


def errors(document: dict):
    return JsonSchemaValidator().validate(contract(), document)


def test_the_shipped_contract_is_a_valid_2020_12_schema():
    # x- annotations are unknown keywords and must not break formal validation.
    Draft202012Validator.check_schema(contract())


def test_a_complete_document_has_no_formal_errors():
    assert errors({**HEAD, "source": JDBC}) == []


def test_an_incomplete_document_is_formally_invalid():
    assert errors({})


def test_the_validator_does_not_depend_on_the_requirement_engine():
    # The walker never entered the union before oneOf support existed; the validator always did.
    assert errors({**HEAD, "source": {"sourceType": "sap"}})


def test_missing_data_is_never_shown_to_the_user():
    # Absence is what `requirements` are for.
    assert map_schema_errors(errors({})) == []


def test_union_container_errors_are_not_shown_to_the_user():
    # `oneOf` cannot tell a wrong discriminator from an unfinished branch, so its message is
    # useless; UnionBranchSelector produces the precise one instead.
    assert map_schema_errors(errors({**HEAD, "source": {"sourceType": "sap"}})) == []
    assert map_schema_errors(errors({**HEAD, "source": {"sourceType": "jdbc"}})) == []


def test_a_wrong_existing_value_is_shown_to_the_user():
    document = {**HEAD, "source": {**JDBC, "sourceTable": 123}}
    issues = map_schema_errors(errors(document))
    assert issues and all(i.severity == "error" for i in issues)
    assert any("/source/sourceTable" == i.path for i in issues)
