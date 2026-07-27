from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

import acdm.mcp_client as mcp_client_module
from acdm.contract_port import McpContractPort
from acdm.models import RequirementsCatalogue


@pytest.mark.asyncio
async def test_stdio_mcp_returns_typed_active_catalogue() -> None:
    async with McpContractPort() as port:
        payload = await port.get_onboarding_requirements("csv", ["bronze"])
    catalogue = RequirementsCatalogue.model_validate(payload)

    assert catalogue.source_type == "csv"
    assert catalogue.target_layers == ["bronze"]
    assert "source.columns" in catalogue.required_paths


@pytest.mark.asyncio
async def test_stdio_mcp_timeout_is_reported(monkeypatch) -> None:
    @asynccontextmanager
    async def stalled_stdio_client(_params):
        await asyncio.sleep(0.05)
        yield None, None

    monkeypatch.setattr(
        mcp_client_module, "stdio_client", stalled_stdio_client
    )
    port = McpContractPort(timeout_seconds=0.01)

    with pytest.raises(RuntimeError, match="nie odpowiedział"):
        await port.list_contract_options()


@pytest.mark.asyncio
async def test_stdio_mcp_reuses_one_initialized_session(monkeypatch) -> None:
    counters = {
        "transport_entered": 0,
        "transport_exited": 0,
        "session_entered": 0,
        "session_exited": 0,
        "initialized": 0,
        "calls": 0,
    }

    @asynccontextmanager
    async def fake_stdio_client(_params):
        counters["transport_entered"] += 1
        try:
            yield object(), object()
        finally:
            counters["transport_exited"] += 1

    class FakeClientSession:
        def __init__(self, _read, _write) -> None:
            pass

        async def __aenter__(self):
            counters["session_entered"] += 1
            return self

        async def __aexit__(self, *_exc) -> None:
            counters["session_exited"] += 1

        async def initialize(self) -> None:
            counters["initialized"] += 1

        async def call_tool(self, tool_name, _arguments):
            counters["calls"] += 1
            return SimpleNamespace(
                isError=False,
                structuredContent={"result": {"tool": tool_name}},
                content=[],
            )

    monkeypatch.setattr(
        mcp_client_module, "stdio_client", fake_stdio_client
    )
    monkeypatch.setattr(
        mcp_client_module, "ClientSession", FakeClientSession
    )
    port = McpContractPort(timeout_seconds=1)

    await port.start()
    first = await port.list_contract_options()
    second = await port.list_contract_options()
    await port.close()

    assert first == second == {"tool": "list_contract_options"}
    assert counters == {
        "transport_entered": 1,
        "transport_exited": 1,
        "session_entered": 1,
        "session_exited": 1,
        "initialized": 1,
        "calls": 2,
    }
