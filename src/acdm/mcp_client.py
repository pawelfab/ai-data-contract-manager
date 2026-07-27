from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
from typing import Any, Protocol

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class McpToolClient(Protocol):
    """Reusable transport lifecycle shared by MCP-backed adapters."""

    async def start(self) -> None: ...

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> Any: ...

    async def close(self) -> None: ...


class StdioMcpClient:
    """One initialized stdio session reused until application shutdown."""

    def __init__(
        self,
        params: StdioServerParameters,
        *,
        timeout_seconds: float,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds musi być większe od zera.")
        self.params = params
        self.timeout_seconds = timeout_seconds
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self._lifecycle_lock = asyncio.Lock()
        self._call_lock = asyncio.Lock()

    async def start(self) -> None:
        if self._session is not None:
            return
        async with self._lifecycle_lock:
            if self._session is not None:
                return
            stack = AsyncExitStack()
            try:
                async with asyncio.timeout(self.timeout_seconds):
                    read, write = await stack.enter_async_context(
                        stdio_client(self.params)
                    )
                    session = await stack.enter_async_context(
                        ClientSession(read, write)
                    )
                    await session.initialize()
            except TimeoutError as exc:
                await stack.aclose()
                raise RuntimeError(
                    "Serwer MCP nie odpowiedział podczas uruchamiania w ciągu "
                    f"{self.timeout_seconds:g} s."
                ) from exc
            except Exception:
                await stack.aclose()
                raise
            self._stack = stack
            self._session = session

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> Any:
        await self.start()
        async with self._call_lock:
            if self._session is None:
                raise RuntimeError("Sesja MCP nie została uruchomiona.")
            try:
                async with asyncio.timeout(self.timeout_seconds):
                    return await self._session.call_tool(
                        tool_name, arguments
                    )
            except TimeoutError as exc:
                raise RuntimeError(
                    f"MCP tool {tool_name!r} nie odpowiedział w ciągu "
                    f"{self.timeout_seconds:g} s."
                ) from exc

    async def close(self) -> None:
        async with self._lifecycle_lock:
            stack = self._stack
            self._stack = None
            self._session = None
            if stack is not None:
                await stack.aclose()
