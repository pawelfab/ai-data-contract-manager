---
module: contract-schema
source_roots:
  - contracts
  - contracts/ux_rules.json
  - examples/contract-rules.json
last_verified: working-tree-2026-08-19
owners: []
---

# Contract schema artifacts

## Responsibility

Hold migration/reference JSON artifacts used to verify data-contract structure and rule
metadata. Production schema, enrichment, canonical-path, validation, and rendering
authority belongs to Contract Forge; ADCM keeps these local copies only as fixtures during
migration. These artifacts are included in documentation freshness tracking.

## Current working-tree facts

- `contracts/contract.json` is the repository-approved migration test fixture (not a production source) and is a JSON Schema draft 2020-12 document with metadata (including `sourceSystemGcpId`), source variants, optional `converter`/`preparator` sections, medallion targets, orchestration, and `x-contract-rules` annotations. The retired `contracts/data-contract.schema.json` path is deliberately absent.
- Fixed-width source columns use the shared `FixedWidthColumnConfig` definition, so its bounds rules are attached to the active source shape.
- `contracts/ux_rules.json` is an opaque local Contract Forge enrichment input/fixture. It contains generic `set_default` rules with `when_path`/`when_value` conditions for ROCKET and SAP source systems. Its supported action vocabulary also reserves provider-neutral `copy_value` and `format_value` actions.
- `examples/contract-rules.json` is an opaque legacy/reference catalog, not executable ADCM policy. Its 12 rules use alias/path details that Forge must compile before production evaluation.
- `tests/test_contract_schema_rules.py::SCHEMA_PATH` points to `contracts/contract.json`; active `*.contract.json` examples and the schema are parsed as JSON.

## Stage 0 verified artifact inventory

- The reachable root requires `metadata`, `source`, `targets`, and `orchestration`. Its
  definition graph reaches 33 of 36 `$defs`, including `ConverterConfig` and
  `PreparatorConfig` together with the source and target component definitions they
  reference.
- `RecordValidationConfig`, `SilverTableConfig`, and `TransformedColumn` are outside the
  reachable root graph. Their rule annotations remain migration/reference evidence; they
  are not inferred to be active Forge policy by ADCM.
- `contract.json` has 14 `x-contract-rules` annotations. The legacy catalog has 12. The
  extra annotations are `targets.bronze.required` and `targets.gold.requires_silver`; the
  two artifacts must not be treated as equivalent.
- Active JSON contract examples are `examples/csv-bronze.contract.json` and
  `examples/fixed-width-all-layers.contract.json`. No agreed production Forge source,
  endpoint, or transport contract appears in this repository, so Stage 3 is
  `BLOCKED_INPUT`.

## Compatibility and tests

The rule test verifies that all 12 legacy rules appear in the schema using only `id`,
`kind`, `message`, and `path`; it also proves the 14-versus-12 rule-count gap and root
reachability boundary. `tests/test_ux_rules.py` verifies unique IDs, supported actions,
canonical target paths, and the requested ROCKET/SAP defaults. Active `*.contract.json`
examples must parse as JSON. These checks inspect fixtures only and do not make them ADCM
runtime policy.

Fixture readers turn missing or malformed JSON into errors that name the affected path and
the read/parse reason. The schema test also reports an owner-approved root-shape mismatch
with the fixture path and expected versus actual required roots.
