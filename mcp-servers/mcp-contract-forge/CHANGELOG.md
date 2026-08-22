# Changelog

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
