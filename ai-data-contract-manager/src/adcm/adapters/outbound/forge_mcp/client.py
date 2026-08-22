import json

from mcp import Client

from adcm.application.ports.forge import ContractForgePort, ForgeEvaluation


class ForgeMcpAdapter(ContractForgePort):
    def __init__(self, url: str):
        self.url = url

    async def evaluate(self, document: dict, *, user_id: str | None = None) -> ForgeEvaluation:
        arguments = {"document": document}
        if user_id is not None:
            arguments["user_id"] = user_id
        async with Client(self.url) as client:
            result = await client.call_tool("evaluate_contract", arguments)
        return ForgeEvaluation.model_validate(_tool_payload(result))


def _tool_payload(result):
    content = getattr(result, "content", []) or []
    if getattr(result, "is_error", False):
        detail = "; ".join(
            text for block in content if (text := getattr(block, "text", None))
        ) or "unknown Forge MCP error"
        raise RuntimeError(f"Contract Forge MCP call failed: {detail}")

    structured = getattr(result, "structured_content", None)
    if structured is not None:
        return structured

    for block in content:
        text = getattr(block, "text", None)
        if not text:
            continue
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            continue
    raise RuntimeError("Contract Forge MCP returned no structured JSON payload")
