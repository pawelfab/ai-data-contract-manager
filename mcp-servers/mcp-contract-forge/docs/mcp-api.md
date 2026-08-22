# MCP API

Primary tool: `evaluate_contract(document: dict) -> Forge API v1`.

The tool returns active requirements, suggestions/defaults/enrichments, validation issues and validity. Suggestions may carry `sourceRef`/`ruleId` for provenance.

The server uses MCP SDK v2. Remote deployment should use Streamable HTTP.
