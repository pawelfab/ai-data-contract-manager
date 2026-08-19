from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from contract_forge.engine import ContractForge
from contract_forge.models import ForgeState, Origin


class ForgeGateway(ABC):
    @abstractmethod
    async def start_session(self) -> ForgeState: ...

    @abstractmethod
    async def get_state(self, session_id: str) -> ForgeState: ...

    @abstractmethod
    async def submit_values(self, session_id: str, values: dict[str, Any], origin: Origin) -> ForgeState: ...

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


class LocalForgeGateway(ForgeGateway):
    """In-process adapter for tests and a zero-network demo. Production path is MCPForgeGateway."""

    def __init__(self, forge: ContractForge):
        self.forge = forge

    async def start_session(self) -> ForgeState:
        return self.forge.start_session()

    async def get_state(self, session_id: str) -> ForgeState:
        return self.forge.get_state(session_id)

    async def submit_values(self, session_id: str, values: dict[str, Any], origin: Origin) -> ForgeState:
        return self.forge.submit_values(session_id, values, origin)


class MCPForgeGateway(ForgeGateway):
    """MCP client with one reusable Streamable HTTP toolset connection.

    Pydantic AI's MCPToolset is used directly so ADCM, not the LLM, controls when
    Contract Forge is called. This keeps the orchestration deterministic.
    """

    def __init__(self, url: str):
        try:
            from pydantic_ai.mcp import MCPToolset
        except ImportError as exc:  # pragma: no cover - optional runtime dependency
            raise RuntimeError('Install MCP extras: pip install -e ".[mcp]"') from exc
        self._toolset = MCPToolset(url, tool_error_behavior="error")
        self._entered = False

    async def __aenter__(self):
        if not self._entered:
            await self._toolset.__aenter__()
            self._entered = True
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._entered:
            self._entered = False
            return await self._toolset.__aexit__(exc_type, exc, tb)
        return None

    async def start_session(self) -> ForgeState:
        raw = await self._toolset.direct_call_tool("start_session", {})
        return ForgeState.model_validate(self._normalize(raw))

    async def get_state(self, session_id: str) -> ForgeState:
        raw = await self._toolset.direct_call_tool("get_state", {"session_id": session_id})
        return ForgeState.model_validate(self._normalize(raw))

    async def submit_values(self, session_id: str, values: dict[str, Any], origin: Origin) -> ForgeState:
        raw = await self._toolset.direct_call_tool(
            "submit_values",
            {"session_id": session_id, "values": values, "origin": origin.value},
        )
        return ForgeState.model_validate(self._normalize(raw))

    @staticmethod
    def _normalize(raw: Any) -> Any:
        if isinstance(raw, dict):
            return raw
        if hasattr(raw, "model_dump"):
            dumped = raw.model_dump(mode="json")
            if isinstance(dumped, dict) and "data" in dumped and isinstance(dumped["data"], dict):
                return dumped["data"]
            return dumped
        for attr in ("data", "structured_content", "structuredContent"):
            value = getattr(raw, attr, None)
            if isinstance(value, dict):
                return value
        content = getattr(raw, "content", None)
        if isinstance(content, list):
            for item in content:
                text = getattr(item, "text", None)
                if text:
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        pass
        raise TypeError(f"Unsupported MCP tool result: {type(raw)!r}")
