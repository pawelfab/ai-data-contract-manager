from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import pytest

import acdm.contract_port as contract_port_module
from acdm.contract_port import McpContractPort
from acdm.models import RequirementsCatalogue


@pytest.mark.asyncio
async def test_stdio_mcp_returns_typed_active_catalogue() -> None:
    port = McpContractPort()

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
        contract_port_module, "stdio_client", stalled_stdio_client
    )
    port = McpContractPort(timeout_seconds=0.01)

    with pytest.raises(RuntimeError, match="nie odpowiedział"):
        await port.list_contract_options()
