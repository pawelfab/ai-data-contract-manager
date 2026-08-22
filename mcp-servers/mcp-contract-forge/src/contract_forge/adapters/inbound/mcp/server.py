from mcp.server import MCPServer

from contract_forge.bootstrap.container import build_container

container = build_container()
mcp = MCPServer("mcp-contract-forge", version="0.4.0")


@mcp.tool()
def evaluate_contract(document: dict, user_id: str | None = None) -> dict:
    """Evaluate current document using schema, rules, defaults and contextual enrichment.

    user_id is optional now and becomes useful when a per-user enrichment repository is
    configured. It is context, not part of the generated contract document.
    """

    return container.evaluate_contract.execute(document, user_id=user_id).model_dump(
        mode="json", by_alias=True
    )
