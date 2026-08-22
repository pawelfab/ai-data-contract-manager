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
  "version": "2",
  "rules": [
    {
      "id": "example.sap.silver_dataset",
      "scope": "system",
      "system": "sap",
      "path": "/silver/tables/0/table/dataset",
      "value": "silver_sap",
      "priority": 10
    }
  ]
}
```

Adding a declarative rule does not require Python code. Extending the JSON file format requires only the JSON repository adapter. Replacing JSON with per-user persistence requires a new `EnrichmentRepositoryPort` adapter.

## Per-user future

ADCM passes `user_id` to Forge as evaluation context. It is not written into the contract YAML. Forge can then combine global/system rules with user-specific rules. The production user id must originate from authenticated identity.
