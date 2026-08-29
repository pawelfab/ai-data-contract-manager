import os
from time import perf_counter
from typing import Any

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse

from contract_forge.adapters.file_definition import FileContractDefinitionRepository
from contract_forge.application.analyzer import ContractAnalyzer
from contract_forge.application.describer import ContractDescriber
from contract_forge.application.observability.app_log_recorder import AppLogRecorder
from contract_forge.adapters.logging.bigquery_app_log_sink import BigQueryAppLogSink
from contract_forge.adapters.logging.local_app_log_sink import LocalAppLogSink
from contract_forge.domain.protocol import ForgeAnalysis, ForgeDescription


def _build_app_log_recorder() -> AppLogRecorder:
    backend = os.getenv("FORGE_LOG_BACKEND", "local").lower()
    log_dir = os.getenv("FORGE_LOG_DIR", "logs")
    if backend == "local":
        sink = LocalAppLogSink(log_dir)
    elif backend == "bigquery":
        project = os.environ["FORGE_BQ_PROJECT"]
        dataset = os.environ["FORGE_BQ_DATASET"]
        table = os.getenv("FORGE_BQ_APP_LOG_TABLE", "app_logs")
        sink = BigQueryAppLogSink(project, dataset, table)
    else:
        raise ValueError(f"Unsupported FORGE_LOG_BACKEND: {backend!r}")
    recorder = AppLogRecorder(sink, environment=os.getenv("FORGE_ENVIRONMENT", "local"))
    recorder.emit("INFO", "configuration_loaded", data={"environment": os.getenv("FORGE_ENVIRONMENT", "local"), "backend": backend})
    return recorder


definitions = FileContractDefinitionRepository(os.getenv("FORGE_CONTRACT_PATH", "resources/contract.json"))
analyzer = ContractAnalyzer(definitions)
describer = ContractDescriber(definitions)
app_log = _build_app_log_recorder()

mcp = MCPServer("Contract Forge")


@mcp.tool()
def contract_analyze(document: dict[str, Any], correlation_id: str | None = None) -> ForgeAnalysis:
    """Analyze the current contract document without mutating it."""
    started = perf_counter()
    app_log.emit("INFO", "contract_analyze_started", correlation_id=correlation_id,
                 data={"document_keys_count": len(document)})
    try:
        result = analyzer.analyze(document)
    except Exception as exc:
        app_log.emit("ERROR", "contract_analyze_failed", correlation_id=correlation_id,
                     duration_ms=(perf_counter() - started) * 1000,
                     data={"error_type": type(exc).__name__})
        raise
    app_log.emit("INFO", "contract_analyze_completed", correlation_id=correlation_id,
                 duration_ms=(perf_counter() - started) * 1000,
                 data={"missing_count": len(result.missing), "diagnostics_count": len(result.diagnostics),
                       "proposal_count": len(result.proposals), "foreign_count": len(result.foreign)})
    return result


@mcp.tool()
def contract_describe(correlation_id: str | None = None) -> ForgeDescription:
    """Describe the external contract definition in a neutral, read-only form."""
    started = perf_counter()
    app_log.emit("INFO", "contract_describe_started", correlation_id=correlation_id)
    try:
        result = describer.describe()
    except Exception as exc:
        app_log.emit("ERROR", "contract_describe_failed", correlation_id=correlation_id,
                     duration_ms=(perf_counter() - started) * 1000,
                     data={"error_type": type(exc).__name__})
        raise
    app_log.emit("INFO", "contract_describe_completed", correlation_id=correlation_id,
                 duration_ms=(perf_counter() - started) * 1000,
                 data={"field_count": len(result.fields)})
    return result


@mcp.custom_route("/health", methods=["GET"])
async def health(_request):
    return JSONResponse({"status": "ok"})


# Development/docker-compose baseline. Production should use an explicit host/origin allowlist.
security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
app = mcp.streamable_http_app(transport_security=security)
