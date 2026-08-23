# ADCM system architecture

This document describes the system-level shape of the repository. Detailed implementation semantics live in service-specific documentation.

## 1. Repository model

ADCM is a monorepo of independently versioned runtime services.

```text
repo/
├── ai-data-contract-manager/
└── mcp-servers/
    └── mcp-contract-forge/
```

Each runtime service owns its own dependencies, tests, version, Dockerfile and runtime configuration.

Services do not import runtime Python code from each other.

## 2. System flow

```text
User / Web
    ↓
ADCM
├─ session / conversation
├─ EvidenceStore
├─ ContractState
├─ deterministic stabilization
│      ↓ mandatory
│   ContractForgePort
│      ↓ MCP
│   Contract Forge
│
└─ PydanticAI semantic layer
       ├─ evidence interpretation
       ├─ semantic conflict detection
       ├─ question composition
       └─ optional context MCPs
            ├─ Atlassian
            ├─ Schema Explorer
            ├─ Repository
            └─ Visualizer
```

Contract Forge is mandatory. Context MCPs are optional/agentic.

## 3. Responsibility boundary

### ADCM

ADCM understands user intent and owns:
- conversation/session state;
- evidence/provenance;
- accepted values and authority;
- `ContractState`;
- semantic interpretation;
- candidate validation and application;
- fixed-point orchestration;
- user-facing interaction;
- YAML rendering.

### Contract Forge

Forge understands the contract and owns:
- raw contract loading/parsing;
- normalized contract semantics;
- JSON Schema validation;
- requirements/defaults;
- requirement discovery;
- deterministic contract rules;
- enrichment;
- stable evaluation results.

### Context MCPs

Context MCPs expose external context or actions. Their output becomes evidence/context or a bounded tool result. They do not mutate ADCM state directly.

## 4. Contract Forge extension axes

Forge isolates two independent reasons to change:

```text
raw contract source
    ↓ ContractSourcePort
raw data
    ↓ ContractParserPort
NormalizedContract
    ↓
Forge engines
```

and:

```text
enrichment storage
    ↓ EnrichmentRepositoryPort
EnrichmentRule[]
    ↓
EnrichmentResolver
```

Changing contract physical layout should normally remain inside the contract-format adapter.

Changing enrichment persistence should normally remain behind the enrichment repository port.

## 5. Runtime stabilization

Conceptually:

```text
user evidence
    ↓
ADCM state
    ↓
Forge.evaluate(effective_document)
    ↓
requirements + derived suggestions + validity/issues
    ↓
ADCM replaces/recomputes derived values
    ↓
semantic resolver proposes evidence-backed candidates
    ↓
deterministic candidate validation/application
    ↓
actual state changed?
    ├─ yes → evaluate again
    └─ no  → fixed point
```

The LLM never controls this loop and never mutates `ContractState` directly.

## 6. Validation vs conversation

Forge keeps separate:
- formal validation;
- formal/fillable requirements;
- requirement discovery.

`valid=True` means that the current effective document satisfies formal contract rules. It does not close the conversation. ADCM may still process later user edits.

## 7. Value authority

Conceptually, direct user evidence and explicitly referenced user evidence outrank derived Forge suggestions.

Exact authority policy belongs to ADCM and should exist in one place.

Observed conventions from context MCPs are advisory evidence unless explicitly promoted by user intent/policy.

## 8. Documentation map

System-wide:
- `architecture-guardrails.md` — mandatory boundaries;
- `CURRENT_STATE.md` — concise implemented cross-service state;
- `DECISIONS.md` — accepted architecture decisions;
- `KNOWN_ISSUES.md` — known/deferred issues.

ADCM:
- `ai-data-contract-manager/docs/architecture.md`

Contract Forge:
- `mcp-servers/mcp-contract-forge/docs/architecture.md`

Generated navigation:
- `docs/generated/repository-map.md`
- `docs/generated/repository-inventory.json`
- `docs/generated/documentation-impact.md`

Current work:
- `docs/active-task/`

Completed implementation history:
- `docs/history/`
