# Source contract format v1

The current source combines JSON Schema keywords (`$defs`, `$ref`, `properties`, `required`, `default`, `enum`, `anyOf`, `items`, constraints) with `x-contract-rules` attached to `$defs` models and root `x-contract-rules-spec` describing the DSL.

Only `adapters/outbound/contract_json_v1` may depend on those physical locations and names.

## Observations for the supplied sample

The supplied sample is useful as the target format shape, but it is not self-contained enough to be treated as a production-valid schema yet. It contains dangling `$ref` references to definitions not present in `$defs`, including `BigQueryTable`, `Column`, `ChecksumConfig`, `BusinessKeyHashConfig`, `BronzeTableConfig`, and `ConverterConfig`.

Also, although several source-config definitions contain `systemZrodlowy`, none is reachable from the current root `properties`. Therefore "ask for source system first" cannot be derived from this exact sample by JSON Schema traversal alone. Progressive discovery must be supplied by a Forge-owned UX/discovery policy (or the final contract schema must expose the source branch). ADCM must not hard-code that workaround.
