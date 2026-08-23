# Stage 09 — Agentic context tools and stabilization

## Goal

Allow a PydanticAI context agent to use configured non-Forge MCPs such as Atlassian/schema/repository/visualizer; store outputs as provenance-aware evidence, then stabilize against Forge until fixed point and render YAML when safe.

## Boundary

Do not implement future MCP business logic inside ADCM; keep tools behind `AgentContextPort`.

## Done when

- Unit tests for the stage pass.
- Existing earlier-stage tests remain green.
- No new dependency crosses a service boundary without a port.
- Documentation for changed public behavior is updated.
