# Stage 08 — PydanticAI heuristics

## Goal

Use PydanticAI structured outputs to map stored evidence to discovered requirements, detect semantic conflicts and compose user questions. Reject candidates without evidence IDs.

## Boundary

PydanticAI does not mutate ContractState or choose validation cadence.

## Done when

- Unit tests for the stage pass.
- Existing earlier-stage tests remain green.
- No new dependency crosses a service boundary without a port.
- Documentation for changed public behavior is updated.
