# Source contract format v1

The current contract source combines JSON Schema with supported `x-contract-*` annotations.

Only `adapters/outbound/contract_json_v1` may depend on the concrete physical layout and names.

## Responsibility layers

```text
JSON Schema
→ formal structure and validity

x-contract-* annotations
→ additional deterministic contract semantics/discoverability

discovery_rules.json
→ order/visibility/presentation of currently fillable requirements

ux_rules.json
→ enrichment policy
```

These layers must remain separate.

## `x-discriminator`

`x-discriminator` marks a `oneOf` as a discriminated union and identifies the property selecting the branch.

Example:

```json
{
  "oneOf": [
    {"$ref": "#/$defs/JdbcSourceConfig"},
    {"$ref": "#/$defs/JsonSourceConfig"}
  ],
  "x-discriminator": {"path": "sourceType"}
}
```

Accepted discriminator values are derived from branch `const`/`enum` values rather than duplicated in the annotation.

Static contract defects such as ambiguous discriminator values or a branch without a usable discriminator value should fail contract/source validation rather than becoming user-document problems.

A `oneOf` without supported discriminator semantics remains atomic for requirement discovery.

## `x-requirement-expand-items`

`x-requirement-expand-items` controls whether requirement discovery may synthesize missing array elements into per-field requirements.

Without it, an array is atomic and is filled as a whole.

With it, Forge may expand missing items only within schema-defined cardinality.

`minItems` and `x-requirement-expand-items` answer different questions:

| keyword | meaning |
|---|---|
| `minItems` | formal minimum cardinality |
| `x-requirement-expand-items` | permission to expose missing item structure as requirements |

Do not infer missing `[0]` only because an array property is required.

Detailed runtime behavior is documented in `requirement-discovery.md`.

## Format evolution

When physical contract layout changes:

1. update/add the concrete format adapter;
2. map the source into the normalized domain;
3. extend normalized models only when semantics truly change;
4. keep Forge engines, MCP protocol and ADCM unchanged whenever normalized semantics remain compatible.

Historical supplied-contract defects/repairs are recorded under `docs/history/`, not in this current-format contract.
