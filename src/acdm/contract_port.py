from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any, Protocol

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from mcp_contract_forge import ContractSchemaService


class ContractPort(Protocol):
    async def list_contract_options(self) -> dict[str, Any]: ...

    async def get_onboarding_requirements(
        self, source_type: str, target_layers: list[str]
    ) -> dict[str, Any]: ...

    async def validate_contract(
        self, contract: dict[str, Any]
    ) -> dict[str, Any]: ...

    async def generate_contract_yaml(
        self, contract: dict[str, Any]
    ) -> dict[str, Any]: ...


class InProcessContractPort:
    """Fast deterministic adapter for tests and single-process development."""

    def __init__(self, service: ContractSchemaService | None = None) -> None:
        self.service = service or ContractSchemaService()

    async def list_contract_options(self) -> dict[str, Any]:
        return self.service.list_contract_options()

    async def get_onboarding_requirements(
        self, source_type: str, target_layers: list[str]
    ) -> dict[str, Any]:
        return self.service.get_onboarding_requirements(
            source_type, target_layers
        ).model_dump(mode="json")

    async def validate_contract(
        self, contract: dict[str, Any]
    ) -> dict[str, Any]:
        return self.service.validate_contract(contract).model_dump(mode="json")

    async def generate_contract_yaml(
        self, contract: dict[str, Any]
    ) -> dict[str, Any]:
        return self.service.generate_contract_yaml(contract).model_dump(
            mode="json"
        )


class McpContractPort:
    """Deterministic stdio client; the LLM never sees the raw MCP toolset."""

    def __init__(
        self,
        *,
        command: str | None = None,
        module: str = "mcp_contract_forge.server",
        timeout_seconds: float = 15.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds musi być większe od zera.")
        self.command = command or sys.executable
        self.module = module
        self.timeout_seconds = timeout_seconds

    async def list_contract_options(self) -> dict[str, Any]:
        return await self._call("list_contract_options", {})

    async def get_onboarding_requirements(
        self, source_type: str, target_layers: list[str]
    ) -> dict[str, Any]:
        return await self._call(
            "get_onboarding_requirements",
            {
                "source_type": source_type,
                "target_layers": target_layers,
            },
        )

    async def validate_contract(
        self, contract: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._call("validate_contract", {"contract": contract})

    async def generate_contract_yaml(
        self, contract: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._call(
            "generate_contract_yaml", {"contract": contract}
        )

    async def _call(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        params = StdioServerParameters(
            command=self.command,
            args=["-m", self.module],
            env=dict(os.environ),
        )
        try:
            async with asyncio.timeout(self.timeout_seconds):
                async with stdio_client(params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool(tool_name, arguments)
        except TimeoutError as exc:
            raise RuntimeError(
                f"MCP tool {tool_name!r} nie odpowiedział w ciągu "
                f"{self.timeout_seconds:g} s."
            ) from exc

        if getattr(result, "isError", False) or getattr(
            result, "is_error", False
        ):
            raise RuntimeError(self._text_content(result) or "Błąd MCP.")

        structured = getattr(result, "structuredContent", None)
        if structured is None:
            structured = getattr(result, "structured_content", None)
        if isinstance(structured, dict):
            if (
                set(structured) == {"result"}
                and isinstance(structured["result"], dict)
            ):
                return structured["result"]
            return structured

        text = self._text_content(result)
        if not text:
            raise RuntimeError(
                f"MCP tool {tool_name!r} nie zwrócił danych JSON."
            )
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise RuntimeError(
                f"MCP tool {tool_name!r} zwrócił wartość inną niż obiekt."
            )
        return parsed

    @staticmethod
    def _text_content(result: Any) -> str:
        parts = []
        for item in getattr(result, "content", []):
            text = getattr(item, "text", None)
            if isinstance(text, str):
                parts.append(text)
        return "\n".join(parts)
