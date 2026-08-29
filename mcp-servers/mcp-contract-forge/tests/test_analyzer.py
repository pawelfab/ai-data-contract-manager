from pathlib import Path

from contract_forge.adapters.file_definition import FileContractDefinitionRepository
from contract_forge.application.analyzer import ContractAnalyzer
from contract_forge.application.describer import ContractDescriber


CONTRACT = Path(__file__).parents[1] / "resources" / "contract.json"


def analyzer() -> ContractAnalyzer:
    return ContractAnalyzer(FileContractDefinitionRepository(str(CONTRACT)))


def test_empty_document_reports_all_required_leaf_values() -> None:
    result = analyzer().analyze({})
    paths = {item.path for item in result.missing}
    assert paths == {
        "/metadata/sourceSystemGcpId",
        "/metadata/id",
        "/metadata/version",
        "/metadata/dataFileId",
        "/source/sourceType",
        "/source/systemZrodlowy",
    }
    assert result.status.valid is True
    assert result.status.complete is False
    assert result.status.clean is True


def test_enrichment_is_reported_even_when_target_is_filled() -> None:
    document = {
        "metadata": {"sourceSystemGcpId": "sap", "id": "sap", "version": "1.0.0", "dataFileId": "x"},
        "source": {"sourceType": "csv", "systemZrodlowy": "sap", "encoding": "CUSTOM"},
    }
    result = analyzer().analyze(document)
    proposal = next(item for item in result.proposals if item.path == "/source/encoding")
    assert proposal.value == "UTF-8"
    assert proposal.origin == "enrichment"


def test_foreign_does_not_make_formal_status_invalid() -> None:
    document = {
        "metadata": {"sourceSystemGcpId": "sap", "id": "sap", "version": "1.0.0", "dataFileId": "x"},
        "source": {"sourceType": "csv", "systemZrodlowy": "sap"},
        "unexpected": 1,
    }
    result = analyzer().analyze(document)
    assert result.status.valid is True
    assert result.status.clean is False
    assert [item.path for item in result.foreign] == ["/unexpected"]


def test_describe_is_neutral_and_contains_paths() -> None:
    description = ContractDescriber(FileContractDefinitionRepository(str(CONTRACT))).describe()
    paths = {field.path_pattern for field in description.fields}
    assert "/metadata/sourceSystemGcpId" in paths
    assert "/silver/tables/*/name" in paths
