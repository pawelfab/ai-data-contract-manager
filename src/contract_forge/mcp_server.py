from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .engine import ContractForge
from .models import Origin


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_forge() -> ContractForge:
    root = _root()
    schema_path = Path(os.getenv("CONTRACT_SCHEMA_PATH", root / "config" / "contract.json"))
    rules_path = Path(os.getenv("CONTRACT_RULES_PATH", root / "config" / "ux_rules_contract_v1.json"))
    deploy_env = os.getenv("ADCM_DEPLOY_ENV", "dev")
    return ContractForge.from_files(schema_path, rules_path, deploy_env=deploy_env)


forge = build_forge()


def create_server():
    try:
        from fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover - optional runtime dependency
        raise RuntimeError('Install MCP extras: pip install -e ".[mcp]"') from exc

    mcp = FastMCP("Contract Forge")

    @mcp.tool
    def list_source_systems() -> list[dict[str, Any]]:
        """List source systems known to enrichment rules."""
        return forge.list_source_systems()

    @mcp.tool
    def start_session() -> dict[str, Any]:
        """Create a canonical contract-building session owned by Contract Forge."""
        return forge.start_session().model_dump(mode="json")

    @mcp.tool
    def get_state(session_id: str) -> dict[str, Any]:
        """Return canonical contract state and current requirements."""
        return forge.get_state(session_id).model_dump(mode="json")

    @mcp.tool
    def submit_values(session_id: str, values: dict[str, Any], origin: str = "user") -> dict[str, Any]:
        """Submit only values currently requested by Contract Forge; then advance enrichment/defaults."""
        try:
            parsed_origin = Origin(origin)
        except ValueError:
            parsed_origin = Origin.USER
        return forge.submit_values(session_id, values, parsed_origin).model_dump(mode="json")

    return mcp


mcp = create_server()


def main() -> None:
    host = os.getenv("CONTRACT_FORGE_HOST", "127.0.0.1")
    port = int(os.getenv("CONTRACT_FORGE_PORT", "8001"))
    mcp.run(transport="http", host=host, port=port, path="/mcp")


if __name__ == "__main__":
    main()
