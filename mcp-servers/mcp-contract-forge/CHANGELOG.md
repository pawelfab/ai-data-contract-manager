# Changelog

## 0.4.1

- Requirement Engine now enters required arrays, so enabling a component (`silver.enabled = true`) discovers its table instead of stopping at `/silver/tables`. Previously those requirements appeared only once enrichment had materialised element 0.
- An absent array is distinguished from a present but empty one; `minItems` is enforced as a cardinality error when a present array is too short. This closes a gap where `files: []` passed as valid because expanding a string array yields no requirements.
- Element expansion requires the explicit `x-requirement-expand-items` annotation: `minItems` states cardinality, the annotation states discoverability. An array is atomic by default and filled as a whole.
- `SilverConfig.tables` and `GoldConfig.entries` are annotated for expansion with `minItems: 1`; `SilverTableConfig.columns` gets `minItems: 1` only, so a column list is still supplied in one piece.

## 0.4.0

- Added progressive requirement discovery with configurable JSON policy and semantic path tokens.
- Added strict/fail-open discovery policy validation.
- Added fillable-requirement filtering so structural parent containers are not exposed as user questions.
- Added `ContractSemanticPaths`; v1 maps source-system semantics to `/metadata/sourceSystemGcpId` inside the contract-format adapter.
- Fixed system enrichment leakage: runtime scope matching now belongs to `EnrichmentResolver` and requires matching source-system context.
- Added global enrichment copy/template support (`valueFrom`, `{/json/pointer}` interpolation) and `pathPattern` targets for later-discovered fields.
- Added global source-system propagation to `metadata.id` and discovered `systemZrodlowy` requirements.
- Enrichment suggestions are gated by currently visible/existing targets so later branches are not created early.
- Preserved the supplied contract as `contract.input.json`; runtime `contract.json` contains a documented minimal repair for dangling `$ref` definitions in the supplied artifact.
- Forge protocol version updated to 0.4.0.

## 0.3.0

- Initial normalized contract, schema/rule evaluation and MCP transport.
