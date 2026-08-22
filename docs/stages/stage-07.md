# Stage 07 — ADCM to Forge integration

## Goal

Implement `ContractForgePort` and MCP adapter. Every document change goes through the deterministic stabilization loop.

## Boundary

Do not expose Forge as a free-choice PydanticAI MCP tool.

## Done when

- Unit tests for the stage pass.
- Existing earlier-stage tests remain green.
- No new dependency crosses a service boundary without a port.
- Documentation for changed public behavior is updated.
