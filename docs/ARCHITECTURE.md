# System architecture

The repository is a monorepo of independently versioned services. ADCM and every MCP server have their own dependencies, virtual environment, tests and deployment artifact.

```text
User/Web
   ↓
ADCM
├─ deterministic core
│  ├─ Session / ContractState
│  ├─ stabilization loop
│  └─ mandatory ContractForgePort ─────→ mcp-contract-forge
│
└─ PydanticAI agentic layer
   ├─ evidence interpretation
   ├─ conflict detection
   ├─ question generation
   └─ optional MCP tools
      ├─ Atlassian
      ├─ Schema Explorer
      ├─ Repository
      └─ Visualizer
```

## Contract Forge boundaries

Forge has two independent extension axes:

```text
raw contract source ─→ ContractSourcePort ─→ ContractParserPort ─→ NormalizedContract

enrichment storage ─→ EnrichmentRepositoryPort ─→ EnrichmentRule[] ─→ EnrichmentResolver
```

ADCM never parses `contract.json` or enrichment configuration.

## Authority of values

Conceptually:

```text
USER_DIRECT
    > USER_REFERENCED
    > USER_ENRICHMENT
    > SYSTEM_ENRICHMENT
    > GLOBAL_ENRICHMENT
    > schema/default suggestion
```

Observed conventions from Schema Explorer are evidence and may create a warning/conflict; they do not automatically overwrite a user-referenced value.
