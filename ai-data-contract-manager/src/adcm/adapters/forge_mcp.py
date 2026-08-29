from time import perf_counter

from mcp import Client
from pydantic import ValidationError

from adcm.application.observability.app_log_recorder import AppLogRecorder
from adcm.domain.errors import ForgeUnavailableError
from adcm.domain.forge import ForgeAnalysis, ForgeDescription

_UNAVAILABLE = "Contract Forge is unavailable"


class ForgeMcpAdapter:
    def __init__(self, url: str, app_log: AppLogRecorder | None = None) -> None:
        self.url = url
        self.app_log = app_log

    async def analyze(self, document: dict, *, correlation_id: str | None = None) -> ForgeAnalysis:
        started = perf_counter()
        self._info("forge_call_started", correlation_id, data={"tool": "contract_analyze"})
        arguments = {"document": document}
        if correlation_id is not None:
            arguments["correlation_id"] = correlation_id
        try:
            async with Client(self.url) as client:
                result = await client.call_tool("contract_analyze", arguments)
            if result.is_error:
                raise ForgeUnavailableError("contract_analyze returned an MCP tool error")
            if result.structured_content is None:
                raise ForgeUnavailableError("contract_analyze returned no structured content")
            analysis = ForgeAnalysis.model_validate(result.structured_content)
        except ValidationError as exc:
            # Niezgodność protokołu jest defektem, nie niedostępnością usługi.
            self._error("forge_call_failed", correlation_id, started, exc, "contract_analyze")
            raise
        except ForgeUnavailableError as exc:
            self._error("forge_call_failed", correlation_id, started, exc, "contract_analyze")
            raise
        except Exception as exc:
            self._error("forge_call_failed", correlation_id, started, exc, "contract_analyze")
            raise ForgeUnavailableError(_UNAVAILABLE) from exc
        self._info(
            "forge_call_completed",
            correlation_id,
            duration_ms=(perf_counter() - started) * 1000,
            data={
                "tool": "contract_analyze",
                "missing_count": len(analysis.missing),
                "diagnostics_count": len(analysis.diagnostics),
                "proposal_count": len(analysis.proposals),
                "foreign_count": len(analysis.foreign),
            },
        )
        return analysis

    async def describe(self, *, correlation_id: str | None = None) -> ForgeDescription:
        started = perf_counter()
        self._info("forge_call_started", correlation_id, data={"tool": "contract_describe"})
        arguments = {"correlation_id": correlation_id} if correlation_id is not None else {}
        try:
            async with Client(self.url) as client:
                result = await client.call_tool("contract_describe", arguments)
            if result.is_error:
                raise ForgeUnavailableError("contract_describe returned an MCP tool error")
            if result.structured_content is None:
                raise ForgeUnavailableError("contract_describe returned no structured content")
            description = ForgeDescription.model_validate(result.structured_content)
        except ValidationError as exc:
            # Niezgodność protokołu jest defektem, nie niedostępnością usługi.
            self._error("forge_call_failed", correlation_id, started, exc, "contract_describe")
            raise
        except ForgeUnavailableError as exc:
            self._error("forge_call_failed", correlation_id, started, exc, "contract_describe")
            raise
        except Exception as exc:
            self._error("forge_call_failed", correlation_id, started, exc, "contract_describe")
            raise ForgeUnavailableError(_UNAVAILABLE) from exc
        self._info(
            "forge_call_completed",
            correlation_id,
            duration_ms=(perf_counter() - started) * 1000,
            data={"tool": "contract_describe", "field_count": len(description.fields)},
        )
        return description

    def _info(self, event: str, correlation_id: str | None, **kwargs) -> None:
        if self.app_log is not None:
            self.app_log.info(event, component="forge_mcp", correlation_id=correlation_id, **kwargs)

    def _error(self, event: str, correlation_id: str | None, started: float, exc: Exception, tool: str) -> None:
        if self.app_log is not None:
            self.app_log.error(
                event,
                component="forge_mcp",
                # Pierwotna przyczyna zostaje tutaj: klient dostaje wyłącznie ogólny
                # komunikat 503, więc bez tego wpisu diagnostyka nie miałaby czego czytać.
                message=str(exc),
                correlation_id=correlation_id,
                duration_ms=(perf_counter() - started) * 1000,
                data={"tool": tool, "error_type": type(exc).__name__},
            )
