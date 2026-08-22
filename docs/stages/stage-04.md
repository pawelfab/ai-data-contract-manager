# Stage 04 — contract_json_v1 adapter

## Goal

Parse the supplied JSON Schema, refs, local x-contract-rules and root x-contract-rules-spec into normalized Forge models.

## Boundary

Do not repair unsupported prose rules silently; report unsupported/invalid source definitions.

## Done when

- Unit tests for the stage pass.
- Existing earlier-stage tests remain green.
- No new dependency crosses a service boundary without a port.
- Documentation for changed public behavior is updated.
