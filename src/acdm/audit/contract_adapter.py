from __future__ import annotations

from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Any

from ..contract_port import ContractPort
from .service import AuditService


class AuditedContractPort:
    """Decorator that audits every request to the contract backend."""

    def __init__(
        self, inner: ContractPort, audit: AuditService
    ) -> None:
        self.inner = inner
        self.audit = audit

    async def list_contract_options(self) -> dict[str, Any]:
        return await self._call(
            "list_contract_options",
            {},
            self.inner.list_contract_options,
        )

    async def get_onboarding_requirements(
        self, source_type: str, target_layers: list[str]
    ) -> dict[str, Any]:
        return await self._call(
            "get_onboarding_requirements",
            {
                "source_type": source_type,
                "target_layers": target_layers,
            },
            lambda: self.inner.get_onboarding_requirements(
                source_type, target_layers
            ),
        )

    async def validate_contract(
        self, contract: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._call(
            "validate_contract",
            {"contract": contract},
            lambda: self.inner.validate_contract(contract),
        )

    async def generate_contract_yaml(
        self, contract: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._call(
            "generate_contract_yaml",
            {"contract": contract},
            lambda: self.inner.generate_contract_yaml(contract),
        )

    async def _call(
        self,
        operation: str,
        arguments: dict[str, Any],
        call: Callable[[], Awaitable[dict[str, Any]]],
    ) -> dict[str, Any]:
        request_payload: dict[str, Any] = {"operation": operation}
        if self.audit.include_mcp_payloads:
            request_payload["arguments"] = arguments
        await self.audit.record(
            "mcp_request",
            request_payload,
            source="mcp-contract-forge",
        )
        started = perf_counter()
        try:
            result = await call()
        except Exception as exc:
            await self.audit.record(
                "mcp_response",
                {
                    "operation": operation,
                    "status": "error",
                    "durationMs": round(
                        (perf_counter() - started) * 1000, 3
                    ),
                    "error": {
                        "type": type(exc).__name__,
                        "message": str(exc),
                    },
                },
                source="mcp-contract-forge",
            )
            raise

        response_payload: dict[str, Any] = {
            "operation": operation,
            "status": "success",
            "durationMs": round((perf_counter() - started) * 1000, 3),
        }
        if self.audit.include_mcp_payloads:
            response_payload["result"] = result
        await self.audit.record(
            "mcp_response",
            response_payload,
            source="mcp-contract-forge",
        )
        return result
