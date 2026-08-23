# Contract Forge architecture

Contract Forge is a deterministic domain service. It understands contract semantics and does not own conversation or LLM interpretation.

## Main flow

```text
raw contract
    ↓ ContractSourcePort
raw data
    ↓ ContractParserPort
NormalizedContract
    ├─ RequirementEngine
    ├─ JsonSchemaValidator
    ├─ RuleEngine
    ├─ RequirementDiscovery
    └─ EnrichmentResolver
    ↓
EvaluateContract
    ↓
ForgeEvaluation
    ↓
MCP evaluate_contract
```

## Normalized domain boundary

`NormalizedContract` isolates Forge engines from the physical source format.

It contains normalized schema/rule semantics, contract metadata and semantic anchors needed by Forge services.

Concrete JSON Schema layout, `$defs`, `$ref` locations and contract-format annotations belong only to the current format adapter.

## Independent change axes

### Contract source/format

```text
ContractSourcePort
    ↓
ContractParserPort
    ↓
NormalizedContract
```

Changing where the raw contract is stored should not require parser changes.

Changing physical contract structure should normally require only a parser/format-adapter change.

### Enrichment persistence

```text
EnrichmentRepositoryPort
    ↓
normalized EnrichmentRule[]
    ↓
EnrichmentResolver
```

Changing enrichment storage must not require changing runtime applicability semantics.

## Determinism

Forge does not use an LLM.

Formal validity is determined by deterministic schema/rule evaluation. Discovery only controls which fillable requirements are exposed now.

## Documentation map

Contract format and annotations:
- `contract-format.md`

Requirements, discovery, arrays, discriminated unions and validation interaction:
- `requirement-discovery.md`

Enrichment:
- `enrichment.md`

Contract rules:
- `rules-engine.md`

Ports/adapters:
- `ports-and-adapters.md`

MCP protocol:
- `mcp-api.md`

Historical repair information:
- `history/contract-repair-note.md`

Use the root `docs/generated/repository-map.md` for mechanical code navigation when required.
