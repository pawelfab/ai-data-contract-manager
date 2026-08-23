# Requirement discovery

Contract Forge separates **formal validation** from **what ADCM should ask for now**.

```text
contract schema / rules
        ↓
formal requirements
        ↓
fillable_requirements
        ↓
RequirementDiscovery
        ↓
ForgeEvaluation.requirements
```

`ForgeEvaluation.valid` is always calculated from the full formal requirement set. Discovery only filters the user-facing set.

## Policy

The current adapter is `JsonDiscoveryPolicyRepository`, reading `resources/discovery_rules.json`.

The supplied policy is intentionally progressive:

1. source system (`@sourceSystem`) only;
2. remaining metadata;
3. orchestration;
4. all remaining currently formal requirements.

`@sourceSystem` is a semantic token. `SemanticPathResolver` maps it through `NormalizedContract.semantic_paths`; the discovery policy does not know the concrete v1 JSON pointer.

## Fail-open and strict mode

A malformed policy produces `DiscoveryPolicyIssue` values. In production these are mapped to normal Forge warnings and discovery falls back safely. With `FORGE_DISCOVERY_STRICT=true`, invalid policy configuration raises immediately so CI/development fails fast.

## Fillable requirements

Structural parents are not questions when their existence follows from filling required children. For example `/metadata` is removed when `/metadata/id` and other child requirements exist. A genuinely fillable array/object leaf such as a columns array remains a requirement.

## Arrays

The Requirement Engine expands structure only as deep as the schema deterministically says it should:

```text
Object:
  required child        → recurse

Array:
  existing elements     → recurse into each
  missing elements      → synthesize up to minItems, only when x-requirement-expand-items
  otherwise             → the array itself is the requirement (atomic, filled as a whole)

minItems                → formal validation issue when a present array is shorter

Optional object/array   → no synthesis unless activated by document/enrichment/rule
```

**Never invent an array index solely because the array property is required.** `SilverConfig.tables` being required does not make `tables: []` invalid on its own — only `minItems` does. Two knobs, two jobs: `minItems` states the cardinality the contract demands, `x-requirement-expand-items` states that Forge may turn those elements into per-field questions. The flag is permission, `minItems` is the count, so a flag without `minItems` expands nothing.

Defaulting to atomic matters for collections a user states in one breath. `SilverTableConfig.columns` carries `minItems: 1` but no annotation, so Forge asks for `/silver/tables/0/columns` and the whole list arrives as one value. Had it been expanded, the question would be `columns/0/name` and `columns/0/type`, the answer would fill exactly one column, the array would then be present — and the remaining columns would be dropped in silence.

A cardinality issue is reported only for an array that is present and too short. An absent array already carries its own requirement, so reporting it twice would be noise.

Known limitation: Forge cannot ask for elements beyond `minItems`. A pipeline with two silver tables discovers only `tables[0]`; adding another needs a mechanism that does not exist yet.

## Enrichment interaction

Discovery controls when an enrichment target is eligible. This prevents a system rule for a later section from materializing that section prematurely. Forge does not recursively apply its own suggestions; ADCM applies derived suggestions and calls Forge again in the fixed-point loop.
