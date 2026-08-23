# Changelog

## 0.5.0

- Support discriminated `oneOf` unions. `properties.source` was a `oneOf` the Requirement Engine never entered, so `sourceType: "sap"` was reported as a **valid** contract with no issues, and no `/source/*` field was ever discovered.
- Add `x-discriminator` as a generic contract annotation and a `UnionBranchSelector`: the discriminator is asked for first (carrying its allowed values), then only the selected branch is walked. An unknown value is an error listing the allowed values; a union without the annotation stays atomic.
- Reject ambiguous unions at load time via `source_linter` — duplicate discriminator values, or a branch with no `const`/`enum` for the discriminator, are contract defects, not user-document problems.
- Add `allowed_values` to `Requirement`, filled for any schema with `const`/`enum`.
- Add `JsonSchemaValidator` (`Draft202012Validator`, a dependency declared since 0.2.0 but never used). `valid` is now decided by full schema validation instead of by whatever the discovery walker found: `valid = not schema_errors and not rule_errors`.
- Add `schema_validation_issue_mapper` so presentation policy lives outside the validator. Missing-data and union-container errors stay out of `issues`; a failed discriminated union is re-reported against the branch the document selected, so a wrong value inside it is not lost.

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
