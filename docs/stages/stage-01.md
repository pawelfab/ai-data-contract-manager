# Stage 01 — API and sessions

## Goal

Build the smallest runnable ADCM service: FastAPI health/session endpoints and an in-memory session repository.

## Boundary

No LLM, no Forge semantics, no persistence abstraction beyond the repository port.

## Done when

- Unit tests for the stage pass.
- Existing earlier-stage tests remain green.
- No new dependency crosses a service boundary without a port.
- Documentation for changed public behavior is updated.
