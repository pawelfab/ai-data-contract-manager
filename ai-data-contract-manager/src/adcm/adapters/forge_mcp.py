from mcp import Client

from adcm.domain.forge import ForgeAnalysis, ForgeDescription


class ForgeMcpAdapter:
    def __init__(self, url: str) -> None:
        self.url = url

    async def analyze(self, document: dict) -> ForgeAnalysis:
        async with Client(self.url) as client:
            result = await client.call_tool("contract_analyze", {"document": document})
        if result.is_error:
            raise RuntimeError("Contract Forge contract_analyze returned an MCP tool error")
        if result.structured_content is None:
            raise RuntimeError("Contract Forge returned no structured content")
        return ForgeAnalysis.model_validate(result.structured_content)

    async def describe(self) -> ForgeDescription:
        async with Client(self.url) as client:
            result = await client.call_tool("contract_describe", {})
        if result.is_error:
            raise RuntimeError("Contract Forge contract_describe returned an MCP tool error")
        if result.structured_content is None:
            raise RuntimeError("Contract Forge returned no structured content")
        return ForgeDescription.model_validate(result.structured_content)
