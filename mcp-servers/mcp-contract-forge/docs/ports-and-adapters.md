# Contract Forge — ports and adapters

Forge isolates two independent sources of change.

## Contract format

`ContractSourcePort` answers only **where raw contract data comes from**. The current adapter is `JsonFileContractSource`.

`ContractParserPort` answers **how a concrete contract format is interpreted**. `contract_json_v1/ContractJsonV1Parser` is the only component that knows the current JSON Schema layout, `$defs`, `$ref`, `x-contract-rules` and `x-contract-rules-spec`.

Flow:

```text
contract file/source
      ↓ ContractSourcePort
raw dict
      ↓ ContractParserPort
NormalizedContract
      ↓
Forge engines
```

Changing the physical source does not require changing the parser. Changing the contract structure requires replacing/adapting only the parser implementation, while `NormalizedContract` and the engines stay stable.

## Enrichment

`EnrichmentRepositoryPort` returns normalized `EnrichmentRule` objects for `EnrichmentContext(user_id, source_system)`.

Current adapters:

- `JsonEnrichmentRepository` — global/system rules from `resources/ux_rules.json`;
- `InMemoryUserEnrichmentRepository` — reference/test adapter showing per-user rules;
- `NoopUserEnrichmentRepository` — default placeholder until user settings storage is introduced;
- `CompositeEnrichmentRepository` — combines repositories without changing the resolver.

A future BigQuery, SQL, Firestore or remote configuration adapter implements the same port. `EvaluateContract` and `EnrichmentResolver` do not change.
