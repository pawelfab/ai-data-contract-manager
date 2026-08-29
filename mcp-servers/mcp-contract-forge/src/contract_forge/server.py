import os
from typing import Any

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse

from contract_forge.adapters.file_definition import FileContractDefinitionRepository
from contract_forge.application.analyzer import ContractAnalyzer
from contract_forge.application.describer import ContractDescriber
from contract_forge.domain.protocol import ForgeAnalysis, ForgeDescription


definitions = FileContractDefinitionRepository(os.getenv("FORGE_CONTRACT_PATH", "resources/contract.json"))
analyzer = ContractAnalyzer(definitions)
describer = ContractDescriber(definitions)

mcp = MCPServer("Contract Forge")


@mcp.tool()
def contract_analyze(document: dict[str, Any]) -> ForgeAnalysis:
    """Analyze the current contract document without mutating it."""
    return analyzer.analyze(document)


@mcp.tool()
def contract_describe() -> ForgeDescription:
    """Describe the external contract definition in a neutral, read-only form."""
    return describer.describe()


@mcp.custom_route("/health", methods=["GET"])
async def health(_request):
    return JSONResponse({"status": "ok"})


# Development/docker-compose baseline. Production should use an explicit host/origin allowlist.
security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
app = mcp.streamable_http_app(transport_security=security)
