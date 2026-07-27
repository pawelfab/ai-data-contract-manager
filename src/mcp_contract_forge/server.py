from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .schema_service import ContractSchemaService

mcp = FastMCP("mcp-contract-forge")
service = ContractSchemaService()


@mcp.tool()
def list_contract_options() -> dict[str, Any]:
    """List source variants and ordered target layers supported by the schema."""
    return service.list_contract_options()


@mcp.tool()
def get_onboarding_requirements(
    source_type: str,
    target_layers: list[str] | None = None,
) -> dict[str, Any]:
    """Return required and optional fields for one active contract slice."""
    return service.get_onboarding_requirements(
        source_type=source_type,
        target_layers=target_layers,
    ).model_dump(mode="json")


@mcp.tool()
def validate_contract(contract: dict[str, Any]) -> dict[str, Any]:
    """Validate a complete draft and return semantic descriptions for errors."""
    return service.validate_contract(contract).model_dump(mode="json")


@mcp.tool()
def generate_contract_yaml(contract: dict[str, Any]) -> dict[str, Any]:
    """Render YAML only when the complete contract passes strict validation."""
    return service.generate_contract_yaml(contract).model_dump(mode="json")


def run() -> None:
    mcp.run()


if __name__ == "__main__":
    run()
