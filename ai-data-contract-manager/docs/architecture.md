# ADCM architecture

## Domain

- `Session`
- `ContractState`
- `EvidenceItem`
- `Authority` / `Provenance`
- advisory issues

## Application

- create session,
- handle message,
- stabilize contract,
- value resolution.

## Outbound ports

- `ContractForgePort` — mandatory and deterministic,
- `HeuristicsPort` — PydanticAI semantic behavior,
- `AgentContextPort` — optional PydanticAI MCP tools,
- `SessionRepositoryPort` — persistence.

## Adapters

- Forge MCP client,
- PydanticAI heuristic agents,
- PydanticAI MCP context agent,
- memory session repository.

The PydanticAI context agent never receives Contract Forge as a tool.
