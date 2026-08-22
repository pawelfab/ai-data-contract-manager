# ADCM ports and adapters

`ContractForgePort` is called by application code and is not agent-selected.

`HeuristicsPort` is implemented by `PydanticAiHeuristicsAdapter` in production and a conservative deterministic adapter for local/unit testing.

`AgentContextPort` is implemented by `PydanticAiMcpContextAdapter` when context MCP URLs are configured. Future Atlassian, repository, schema explorer and visualizer servers plug in here without changing ContractState or Forge integration.
