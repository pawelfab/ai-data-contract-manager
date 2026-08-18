---
module: contract-schema
source_roots:
  - contracts
  - examples/contract-rules.json
last_verified: working-tree-2026-08-18
owners: []
---

# Contract schema artifacts

## Responsibility

Hold the JSON Schema and legacy rule catalog used to define and verify data-contract structure and cross-field rules. These artifacts are public schema inputs and are included in documentation freshness tracking.

## Current working-tree facts

- `contracts/contract.json` is a JSON Schema draft 2020-12 document with ADCM metadata, source variants, medallion targets, orchestration, and `x-contract-rules` annotations.
- `examples/contract-rules.json` is the legacy rule source used by `tests/test_contract_schema_rules.py`.
- `tests/test_contract_schema_rules.py::SCHEMA_PATH` still points to `contracts/data-contract.schema.json`, but that tracked path is deleted in the current worktree. This is a confirmed unresolved mismatch, not an agent-workflow migration change.

## Compatibility and tests

The rule test expects all legacy rules to appear in the schema using only `id`, `kind`, `message`, and `path`, with 12 unique IDs and no `x-acdm-rule-catalog`. Active `*.contract.json` examples must parse as JSON. Until the path mismatch is resolved by the owning change, the two schema tests fail before validating content.

