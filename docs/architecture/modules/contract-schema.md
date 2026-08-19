---
module: contract-schema
source_roots:
  - contracts
  - contracts/ux_rules.json
  - examples/contract-rules.json
last_verified: working-tree-2026-08-18
owners: []
---

# Contract schema artifacts

## Responsibility

Hold the JSON Schema, enrichment/UX rule definitions, and legacy rule catalog used to define and verify data-contract structure and cross-field rules. These artifacts are public Contract Forge inputs and are included in documentation freshness tracking.

## Current working-tree facts

- `contracts/contract.json` is a JSON Schema draft 2020-12 document with metadata (including `sourceSystemGcpId`), source variants, optional `converter`/`preparator` sections, medallion targets, orchestration, and `x-contract-rules` annotations.
- Fixed-width source columns use the shared `FixedWidthColumnConfig` definition, so its bounds rules are attached to the active source shape.
- `contracts/ux_rules.json` contains generic `set_default` rules with `when_path`/`when_value` conditions for ROCKET and SAP source systems. Its supported action vocabulary also reserves provider-neutral `copy_value` and `format_value` actions.
- `examples/contract-rules.json` remains the legacy rule source used to verify the corresponding annotations in `contracts/contract.json`.
- `tests/test_contract_schema_rules.py::SCHEMA_PATH` points to `contracts/contract.json`; active `*.contract.json` examples and the schema are parsed as JSON.

## Compatibility and tests

The rule test expects all legacy rules to appear in the schema using only `id`, `kind`, `message`, and `path`, with 12 unique IDs and no `x-acdm-rule-catalog`. `tests/test_ux_rules.py` verifies unique IDs, supported actions, canonical target paths, and the requested ROCKET/SAP defaults. Active `*.contract.json` examples must parse as JSON.
