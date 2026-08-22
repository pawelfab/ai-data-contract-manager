# Stage 02 — Mutable contract state

## Goal

Support full JSON Pointer paths including arrays, editable fields after completion, last accepted user value, authority and provenance.

## Boundary

Do not encode contract schema or workflow stages in ContractState.

## Done when

- Unit tests for the stage pass.
- Existing earlier-stage tests remain green.
- No new dependency crosses a service boundary without a port.
- Documentation for changed public behavior is updated.
