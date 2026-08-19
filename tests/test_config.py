import pytest
from pydantic import ValidationError

from adcm.config import Settings


def test_default_contract_forge_selection_uses_the_mock_reference_adapter() -> None:
    settings = Settings()

    assert settings.contract_forge_transport == "mock"
    assert settings.contract_forge_source is None
    assert settings.contract_forge_endpoint is None


def test_fixture_source_is_an_opaque_configuration_reference() -> None:
    settings = Settings(
        contract_forge_transport="fixture",
        contract_forge_source="fixtures/not-present-in-this-test.json",
    )

    assert settings.contract_forge_source == "fixtures/not-present-in-this-test.json"
    assert settings.contract_forge_endpoint is None


def test_remote_contract_forge_selection_requires_source_and_endpoint() -> None:
    settings = Settings(
        contract_forge_transport="remote",
        contract_forge_source="contract-forge://production/schema/v1",
        contract_forge_endpoint="https://forge.example.test/mcp",
    )

    assert settings.contract_forge_transport == "remote"


def test_unsupported_contract_forge_transport_fails_early() -> None:
    with pytest.raises(ValidationError):
        Settings(contract_forge_transport="in_process")


@pytest.mark.parametrize(
    ("settings", "error"),
    [
        ({"contract_forge_transport": "fixture"}, "requires contract_forge_source"),
        (
            {"contract_forge_transport": "fixture", "contract_forge_endpoint": "https://forge"},
            "requires contract_forge_source",
        ),
        (
            {"contract_forge_transport": "remote"},
            "requires contract_forge_source and contract_forge_endpoint",
        ),
        (
            {
                "contract_forge_transport": "mock",
                "contract_forge_source": "fixtures/contract.json",
            },
            "does not accept contract_forge_source or contract_forge_endpoint",
        ),
        (
            {
                "contract_forge_transport": "fixture",
                "contract_forge_source": "fixtures/contract.json",
                "contract_forge_endpoint": "https://forge",
            },
            "does not accept contract_forge_endpoint",
        ),
        (
            {"contract_forge_transport": "fixture", "contract_forge_source": "  "},
            "contract_forge_source must be non-blank",
        ),
        (
            {
                "contract_forge_transport": "remote",
                "contract_forge_source": "contract-forge://production/schema/v1",
                "contract_forge_endpoint": "  ",
            },
            "contract_forge_endpoint must be non-blank",
        ),
    ],
)
def test_contract_forge_selection_rejects_conflicting_or_incomplete_values(
    settings: dict[str, str], error: str
) -> None:
    with pytest.raises(ValidationError, match=error):
        Settings(**settings)
