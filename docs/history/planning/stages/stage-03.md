# Stage 03 — Forge normalized domain

## Goal

Define `NormalizedContract`, schema/rule/evaluation models so application services do not depend on raw JSON structure.

## Boundary

Do not expose raw `$defs`/`x-contract-rules` outside the adapter boundary.

## Done when

- Unit tests for the stage pass.
- Existing earlier-stage tests remain green.
- No new dependency crosses a service boundary without a port.
- Documentation for changed public behavior is updated.
