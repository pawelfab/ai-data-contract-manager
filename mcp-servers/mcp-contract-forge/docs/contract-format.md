# Source contract format v1

The current source combines JSON Schema keywords (`$defs`, `$ref`, `properties`, `required`, `default`, `enum`, `anyOf`, `items`, constraints) with `x-contract-rules` attached to `$defs` models and root `x-contract-rules-spec` describing the DSL.

Only `adapters/outbound/contract_json_v1` may depend on those physical locations and names.

## Layers

```text
JSON Schema                  → what is valid
x-contract-* annotations     → how the structure is discovered
discovery_rules.json         → in which order requirements are shown
```

Keeping them apart is what stops a UX wish from being encoded as a fake constraint, and a real constraint from silently changing the conversation.

## `x-discriminator`

Marks a `oneOf` as a discriminated union and names the property that selects the branch:

```json
"source": {
  "oneOf": [
    {"$ref": "#/$defs/JdbcSourceConfig"},
    {"$ref": "#/$defs/JsonSourceConfig"},
    {"$ref": "#/$defs/TxtSourceConfig"},
    {"$ref": "#/$defs/FixedWidthSourceConfig"}
  ],
  "x-discriminator": { "path": "sourceType" }
}
```

The accepted values are read from each branch's `const` (or `enum`) for that property — the
annotation never repeats them, so it cannot drift from the branches. A `oneOf` without the
annotation is not selectable and stays atomic: the union node itself is the requirement.

Two defects are static properties of the contract and therefore fail at **load** time, through
`source_linter`, rather than surfacing later as a puzzling problem with a user's document:

- two branches claiming the same discriminator value;
- a branch that declares no `const`/`enum` for the discriminator.

## `x-requirement-expand-items`

A boolean annotation on an array property. Without it an array is **atomic**: the array itself is the requirement and is filled as a whole. With it, Forge may expand missing elements into per-field requirements — bounded by `minItems`, never beyond.

```json
"tables": {
  "type": "array",
  "items": { "$ref": "#/$defs/SilverTableConfig" },
  "minItems": 1,
  "x-requirement-expand-items": true
}
```

The two keywords answer different questions and are deliberately independent:

| keyword | answers | affects |
|---|---|---|
| `minItems` | how many elements must exist | validation, and the number of elements expansion may cover |
| `x-requirement-expand-items` | may Forge ask about an element's fields | discovery only |

In the shipped contract the annotation is on `SilverConfig.tables` and `GoldConfig.entries` — structural lists of pipeline objects whose fields are individually answerable. It is deliberately absent from `SilverTableConfig.columns`, `BusinessKeyHashConfig.columns`, `FixedWidthConfig.columns` and `PreparatorInput.files`, which are data collections supplied in one piece.

## Observations for the supplied sample

The supplied sample is useful as the target format shape, but it is not self-contained enough to be treated as a production-valid schema yet. It contains dangling `$ref` references to definitions not present in `$defs`, including `BigQueryTable`, `Column`, `ChecksumConfig`, `BusinessKeyHashConfig`, `BronzeTableConfig`, and `ConverterConfig`.

Also, although several source-config definitions contain `systemZrodlowy`, none is reachable from the current root `properties`. Therefore "ask for source system first" cannot be derived from this exact sample by JSON Schema traversal alone. Progressive discovery must be supplied by a Forge-owned UX/discovery policy (or the final contract schema must expose the source branch). ADCM must not hard-code that workaround.
