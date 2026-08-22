from contract_forge.adapters.inbound.mcp.server import mcp
from contract_forge.bootstrap.settings import Settings
if __name__ == "__main__":
    s=Settings(); mcp.run(transport="streamable-http",host=s.host,port=s.port,streamable_http_path="/mcp",json_response=True)
