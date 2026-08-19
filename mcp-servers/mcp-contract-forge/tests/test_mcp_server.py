import pytest

pytest.importorskip("mcp")

from contract_forge.mcp_server import create_server


def test_mcp_server_registers_contract_forge_tools():
    server = create_server()

    assert server.name == "Contract Forge"
