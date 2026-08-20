from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .contracts import JsonFileContractAdapter
from .engine import ContractForge
from .models import Origin


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _service_path(env_name: str, default: str) -> Path:
    root = _root()
    configured = Path(os.getenv(env_name, default))
    return configured if configured.is_absolute() else root / configured


def build_forge() -> ContractForge:
    """Build the singleton Forge.

    A ``ContractDefinitionError`` here is deliberately fatal: a contract whose rules
    Forge cannot execute must not serve sessions.
    """
    load_dotenv(_root() / ".env", override=False)
    schema_path = _service_path("CONTRACT_FORGE_SCHEMA_PATH", "config/contract.json")
    rules_path = _service_path("CONTRACT_FORGE_RULES_PATH", "config/ux_rules_contract_v1.json")
    deploy_env = os.getenv("CONTRACT_FORGE_DEPLOY_ENV", "dev")
    rules = json.loads(rules_path.read_text(encoding="utf-8"))
    return ContractForge(JsonFileContractAdapter(schema_path), rules, deploy_env=deploy_env)


forge = build_forge()


def create_server():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover - optional runtime dependency
        raise RuntimeError('Install Contract Forge dependencies: pip install -e "."') from exc

    host = os.getenv("CONTRACT_FORGE_HOST", "127.0.0.1")
    port = int(os.getenv("CONTRACT_FORGE_PORT", "8001"))
    mcp = FastMCP(
        "Contract Forge",
        host=host,
        port=port,
        streamable_http_path="/mcp",
    )

    @mcp.tool()
    def list_source_systems() -> list[dict[str, Any]]:
        """List source systems known to enrichment rules."""
        return forge.list_source_systems()

    @mcp.tool()
    def start_session() -> dict[str, Any]:
        """Create a canonical contract-building session owned by Contract Forge."""
        return forge.start_session().model_dump(mode="json")

    @mcp.tool()
    def get_state(session_id: str) -> dict[str, Any]:
        """Return canonical contract state and current requirements."""
        return forge.get_state(session_id).model_dump(mode="json")

    @mcp.tool()
    def get_editable_fields(session_id: str) -> list[dict[str, Any]]:
        """List the contract values the user may deliberately change right now.

        Arrays are listed as a single unit; submit a replacement for the whole array
        rather than a per-index path.
        """
        return [field.model_dump(mode="json") for field in forge.editable_fields(session_id)]

    @mcp.tool()
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
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
