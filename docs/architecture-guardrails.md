# Architecture Guardrails and Evolution Rules

## Purpose

This document is a mandatory architecture contract for future feature work, refactors and LLM-assisted implementation sessions. Read it before planning or implementing a change.

The goal is not to freeze the design. The goal is to keep change local: a feature should modify the smallest responsible component and must not leak implementation details across service boundaries.

## Core principle: isolate reasons to change

A component that changes because of one reason must not force unrelated parts of the system to change.

Examples:

- A new `contract.json` structure is a Contract Forge adapter concern, not an ADCM concern.
- A new enrichment storage backend is an `EnrichmentRepositoryPort` adapter concern, not an evaluation-engine or ADCM concern.
- A new LLM provider is an ADCM outbound-adapter concern, not a domain/use-case concern.
- A new context MCP such as Atlassian, repository, schema explorer or visualizer is integrated through the context/tool boundary; it must not be added to Contract Forge.
- A deployment-specific logging destination must be selected by a logging adapter/bootstrap configuration, not by business/domain code.

## Service boundaries are mandatory

### AI Data Contract Manager (ADCM)

ADCM owns:

- user sessions and chat history;
- evidence and provenance;
- user-value history and authority/priority policy;
- PydanticAI semantic interpretation;
- optional/agentic context MCP tools;
- the deterministic stabilization loop;
- deciding when a human decision is required;
- final conversation responses and YAML rendering.

ADCM must NOT:

- parse or understand `contract.json`, `$defs`, `$ref`, `x-contract-rules` or `x-contract-rules-spec`;
- implement Contract Forge validation rules;
- know the persistence format of enrichment rules;
- hard-code source-system dictionaries to replace LLM heuristics;
- let the LLM mutate `ContractState` directly;
- let the LLM decide whether mandatory Forge validation should run.

### MCP Contract Forge

Contract Forge owns:

- loading raw contract sources;
- translating the current contract format into `NormalizedContract`;
- schema requirements and defaults;
- deterministic `x-contract-rules` evaluation where supported;
- enrichment resolution;
- returning a stable Forge API response to ADCM.

Contract Forge must NOT:

- own user conversations;
- maintain chat history;
- use an LLM to guess contract values;
- import ADCM runtime code;
- expose raw contract-format details as requirements for ADCM to interpret.

## Mandatory/agentic MCP split

Contract Forge is a mandatory deterministic dependency:

```text
ADCM stabilization loop -> ContractForgePort -> MCP adapter -> Contract Forge
```

It is NOT placed in the PydanticAI agent's free tool-choice set.

Context MCPs are optional/agentic tools:

```text
PydanticAI -> Atlassian / Repository / Schema Explorer / Visualizer / future context MCPs
```

The agent may choose these tools to collect or present context, but ADCM remains responsible for accepting values, provenance, priority and state changes.

## Contract format evolution

The current contract format is isolated behind:

```text
ContractSourcePort -> ContractParserPort -> contract_json_v1 adapter -> NormalizedContract
```

Only the adapter for the concrete format may know details such as `$defs`, `$ref`, `required`, `default`, `x-contract-rules` and `x-contract-rules-spec`.

When the file structure changes:

1. add or modify a format adapter, e.g. `contract_json_v2`;
2. map the new format to the existing normalized domain model;
3. extend the normalized model only if the *semantics* changed and the old model cannot represent the new meaning;
4. keep `EvaluateContract`, ADCM and the MCP wire protocol unchanged whenever semantics remain compatible.

A contract-format change that requires edits across ADCM is an architecture warning and must be justified before implementation.

## Enrichment evolution

The evaluation engine asks an `EnrichmentRepositoryPort` for normalized `EnrichmentRule` objects. It must not read JSON, BigQuery, SQL or another persistence format directly.

Current and future adapters may include:

```text
JsonEnrichmentRepository
UserEnrichmentRepository
BigQueryEnrichmentRepository
SqlEnrichmentRepository
RemoteConfigEnrichmentRepository
CompositeEnrichmentRepository
```

The rules are data, not user-supplied Python code.

Expected authority order is conceptually:

```text
USER_DIRECT
> USER_REFERENCED (e.g. Jira explicitly selected by the user)
> USER_ENRICHMENT
> SYSTEM_ENRICHMENT
> GLOBAL_ENRICHMENT
> DEFAULT
```

Observed conventions from schema/repository inspection are evidence and may trigger a warning/human decision; they must not silently override an explicit user or user-referenced value.

Adding user-specific enrichment must normally require a new repository/storage adapter and bootstrap wiring, not changes in ADCM core or Forge evaluation logic.

## LLM rules

PydanticAI is an adapter/orchestration layer for non-deterministic semantic work. Use it for:

- intent interpretation;
- matching evidence to currently discovered Forge requirements;
- interpreting Jira/wiki/text attachments;
- detecting likely inconsistencies and typos;
- choosing optional context tools;
- composing questions.

Do NOT use it for deterministic work that ordinary code can guarantee, including:

- contract validation;
- priority comparison;
- storing state;
- applying a value to the contract;
- deciding whether Forge validation is mandatory;
- replacing explicit rule engines with prompt text.

Every LLM-derived candidate must be grounded in known evidence. The LLM references evidence; ADCM assigns authority/provenance from the trusted stored source instead of trusting an authority value invented by the model.

## Change strategy

Prefer small vertical changes with explicit boundaries:

```text
small contract/interface
-> implementation in one responsible component
-> unit tests
-> adapter/integration test
-> only then connect the next component
```

Do not implement abstractions for hypothetical requirements. Do preserve known architectural invariants such as editable fields, full JSON Pointer paths, provenance, revalidation and independent services.

## Anti-patterns / stop conditions

Stop and review the architecture before merging if a change causes one of these:

- `contract.json` parsing code appears in ADCM;
- ADCM imports Python classes from `contract_forge`;
- Forge imports ADCM classes;
- an enrichment JSON/database query appears inside `EnrichmentResolver`;
- a user-specific rule requires an `if user_id == ...` branch in core logic;
- a new MCP requires edits to the stabilization algorithm despite being only a context provider;
- the LLM directly edits `ContractState` or chooses authority/priority;
- changing a contract-format field name requires edits in several services;
- environment-specific GCP/local branches appear inside use cases/domain code;
- a large orchestrator begins accumulating logic that belongs to ports, adapters or domain services.

## Architecture test for every feature plan

Before implementation, answer:

1. What is the single primary reason this feature changes the system?
2. Which service owns that responsibility?
3. Which existing port is the correct boundary?
4. If no port exists, is the dependency truly external/replaceable enough to justify a new one?
5. Can the change be implemented without changing unrelated services?
6. What contract/unit/integration test proves that the boundary still holds?
7. If the contract format or enrichment storage changes, can ADCM remain untouched?

If the answer to 7 is "no", the design must be reviewed before implementation.
