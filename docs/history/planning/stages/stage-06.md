# Stage 06 — Forge MCP boundary

## Goal

Expose one primary `evaluate_contract(document)` MCP tool using MCP SDK v2/Streamable HTTP for remote deployment.

## Boundary

Do not split a single evaluation into many agent-oriented tools unless a real API need appears.

## Done when

- Unit tests for the stage pass.
- Existing earlier-stage tests remain green.
- No new dependency crosses a service boundary without a port.
- Documentation for changed public behavior is updated.
