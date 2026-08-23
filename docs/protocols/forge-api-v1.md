# Forge API v1

ADCM depends only on the stable Forge evaluation contract, not on the concrete structure of `contract.json`.

## Evaluation response

The response contains:

- `requirements`: **currently visible, fillable requirements**. Structural parents are omitted when their existence follows from filling child requirements. Discovery may intentionally expose only a subset of the formal requirements. An array is an atomic requirement filled as a whole, unless the contract explicitly marks it for element expansion — so `expectedType: "array"` means "send me the list", not "send me the first element".
- `suggestions`: deterministic schema defaults/enrichment values with source/provenance metadata.
- `issues`: validation/configuration issues. Discovery-policy configuration warnings are mapped here rather than becoming a new transport-specific field.
- `valid`: final validity decided by a full JSON Schema validation of the document, never by whichever requirements the discovery walker happened to produce. It means **"this contract is finally correct"**, not "the conversation can continue" — an in-progress document is legitimately invalid while `requirements` are still open, and ADCM must drive the conversation from `requirements`.
- `forge_version`: implementation version.

A `Requirement` may include presentation metadata (`displayName`, `helpText`) derived from the schema or discovery configuration. ADCM should use these values and the canonical path when composing questions; it must not invent a business meaning for ambiguous identifiers.

A `Requirement` may also carry `allowedValues` — the values Forge will accept there, taken from the schema's `const`/`enum` or from a union discriminator. ADCM offers them to the user and rejects any candidate outside the set, checking membership generically; it never interprets what a value means or which part of the contract it selects.

`issues` reports problems with values that are already present. It deliberately does **not** list what is still missing — that is what `requirements` are for.

## Important invariants

- The wire API does not expose raw `$defs`, `$ref` or `x-contract-rules` for ADCM to interpret.
- Discovery never makes a formally invalid document valid.
- Forge suggestions are not user values and may not silently override stronger user authority in ADCM.
- Contract format changes should remain isolated behind the Forge contract parser adapter whenever normalized semantics stay compatible.
