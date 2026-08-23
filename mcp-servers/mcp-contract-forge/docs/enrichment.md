# Enrichment architecture

Enrichment is deterministic Forge behavior and is deliberately separate from the source `contract.json` parser.

## Stable domain model

External enrichment configuration is normalized to:

- `EnrichmentContext` — current user and source system;
- `EnrichmentRule` — target path, value, conditions, scope, priority and provenance;
- `EnrichmentCondition` — declarative predicates.

`EnrichmentResolver` consumes only these models. It does not know whether rules came from JSON, a database or a remote service.

## Precedence

Within Forge enrichment:

```text
USER enrichment
    > SYSTEM enrichment
    > GLOBAL enrichment
```

The resulting suggestions are still derived values. In ADCM they remain below:

```text
USER_DIRECT
USER_REFERENCED (for example Jira explicitly selected by the user)
```

Therefore a user/Jira value is never silently overwritten by enrichment.

## Current JSON adapter

`resources/ux_rules.json` is only the current storage format. Example:

```json
{
  "version": "6",
  "rules": [
    {
      "id": "example.silver_dataset",
      "scope": "global",
      "path": "/silver/tables/0/table/dataset",
      "value": "{/metadata/sourceSystemGcpId}_silver",
      "priority": 100
    }
  ]
}
```

Adding a declarative rule does not require Python code. Extending the JSON file format requires only the JSON repository adapter. Replacing JSON with per-user persistence requires a new `EnrichmentRepositoryPort` adapter.

## Requirement completeness

`EnrichmentCondition` supports a fourth predicate beside `equals` and `exists`:

```json
{
  "path": "/source",
  "requirementsComplete": true
}
```

It is true when no still-missing formal `Requirement` has that exact path or lies under it.
`EvaluateContract` derives the set from the complete formal requirement list, before
`fillable_requirements()` and before discovery, and passes it to `resolve_enrichment()` as the
mandatory `open_requirement_paths` argument. Completeness is therefore independent of which
question is currently visible.

This is not a validity check. Formal schema/rule errors are reported as issues and may keep
`valid=false` even when every requirement under a prefix has been answered.

## Ordering optional branches

Requirement completeness is what makes a layer chain expressible as data:

```text
/source complete            → /bronzeTable = {}
/bronzeTable complete       → /silver/enabled, /gold/enabled
```

An activating scaffold assigns `{}` and requires `exists=false`; every rule that fills that
container requires `exists=true`. The two groups can never appear in the same evaluation, so a
scaffold cannot overwrite children that already hold values. Do not rely on priority ordering or
on consumer-side merge behavior for that guarantee — express it in the conditions.

Values assigned as whole arrays (for example `"/bronzeTable/columns": []`) stay atomic. Enrichment
never creates `/bronzeTable/columns/0`; array expansion is a contract decision driven by `minItems`
plus `x-requirement-expand-items`.

## Optional branch activation

An enrichment may activate a missing optional schema branch by targeting its first leaf, for
example `/converter/enabled`. Forge verifies that the target exists in the schema and is directly
inside one missing optional container. A deeper rule such as a nested dataset value remains
ineligible until its parent branch is active or discovery exposes that requirement. This permits
declarative component activation without materializing hidden subtrees prematurely.

## Per-user future

ADCM passes `user_id` to Forge as evaluation context. It is not written into the contract YAML. Forge can then combine global/system rules with user-specific rules. The production user id must originate from authenticated identity.
