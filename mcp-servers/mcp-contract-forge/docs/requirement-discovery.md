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

## Enrichment interaction

Discovery controls when an enrichment target is eligible. This prevents a system rule for a later section from materializing that section prematurely. Forge does not recursively apply its own suggestions; ADCM applies derived suggestions and calls Forge again in the fixed-point loop.
