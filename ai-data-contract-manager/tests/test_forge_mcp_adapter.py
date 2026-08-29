from types import SimpleNamespace

import pytest

from adcm.adapters import forge_mcp
from adcm.adapters.forge_mcp import ForgeMcpAdapter


@pytest.mark.asyncio
async def test_adapter_propagates_correlation_id_as_tool_metadata(monkeypatch) -> None:
    calls = []

    class FakeClient:
        def __init__(self, url: str) -> None:
            self.url = url

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def call_tool(self, name: str, arguments: dict):
            calls.append((name, arguments))
            if name == "contract_analyze":
                content = {
                    "protocol_version": "1.0",
                    "definition_version": "fake",
                    "status": {"valid": True, "complete": True, "clean": True},
                }
            else:
                content = {"protocol_version": "1.0", "definition_version": "fake", "fields": []}
            return SimpleNamespace(is_error=False, structured_content=content)

    monkeypatch.setattr(forge_mcp, "Client", FakeClient)
    adapter = ForgeMcpAdapter("http://forge/mcp")

    await adapter.describe(correlation_id="corr-1")
    await adapter.analyze({"metadata": {}}, correlation_id="corr-1")

    assert calls == [
        ("contract_describe", {"correlation_id": "corr-1"}),
        ("contract_analyze", {"document": {"metadata": {}}, "correlation_id": "corr-1"}),
    ]
