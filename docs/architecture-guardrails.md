# ADCM architecture guardrails

> **Status:** authoritative architecture contract for the repository  
> **Scope:** ADCM, Contract Forge, context MCPs and cross-service integration  
> **Priority:** these rules take precedence over local implementation plans when they conflict

## 1. Architectural objective

Keep reasons to change isolated.

A feature should modify the smallest responsible component and must not leak implementation details across service boundaries.

The central invariant is:

> **ADCM understands the user. Contract Forge understands the contract.**

The system should be deterministic where ordinary code can guarantee correctness and semantic/agentic only where interpretation is genuinely required.

## 2. Service ownership

### ADCM owns

- conversation and session state;
- evidence and provenance;
- accepted user-value history;
- authority/priority policy;
- `ContractState`;
- PydanticAI semantic interpretation;
- candidate extraction;
- deterministic candidate validation;
- fixed-point stabilization;
- optional context MCP use;
- user questions, warnings and final responses;
- YAML rendering.

### Contract Forge owns

- contract source loading;
- concrete contract-format parsing;
- `NormalizedContract`;
- JSON Schema semantics and formal validation;
- formal/fillable requirements;
- requirement discovery;
- defaults and deterministic contract rules;
- union/discriminator semantics;
- enrichment resolution;
- requirement presentation metadata;
- Forge issues and stable Forge API responses.

### Context MCPs own

Tool-specific retrieval or actions such as Jira, repository, schema exploration or visualization.

They normally return evidence/context or perform a bounded action. They do not own ADCM state.

## 3. Service boundaries

Runtime services communicate through explicit protocol/port boundaries.

Forbidden:
- direct Python runtime imports between ADCM and Forge;
- parsing `contract.json` in ADCM;
- schema/contract branches such as `if source_type == "jdbc"` in ADCM core/application logic;
- conversation/session ownership in Forge;
- JSON Schema validation in ADCM;
- LLM-controlled mandatory Forge evaluation;
- LLM mutation of `ContractState`;
- deployment-specific infrastructure logic inside domain/use-case code.

Concrete paths supplied by Forge may pass through ADCM as data. ADCM must not hard-code their contract meaning.

If a structural contract change requires ADCM changes while normalized semantics and protocol remain compatible:

> **STOP — the contract boundary is leaking.**

## 4. Deterministic vs semantic responsibilities

Use an LLM for:
- intent interpretation;
- matching evidence to requirements;
- semantic conflict detection;
- typo/phrase interpretation;
- question wording;
- optional context-tool selection.

Use deterministic code for:
- formal contract validation;
- contract/rule interpretation;
- evidence existence checks;
- path/type/allowed-value checks;
- structural safety;
- authority resolution;
- state mutation;
- fixed-point progress;
- mandatory Forge execution.

The flow remains:

```text
Evidence
   ↓
LLM
   ↓
Candidate
   ↓
deterministic ADCM validation
   ↓
ContractState
```

Candidate acceptance and actual state mutation are different concepts. Fixed-point progress must depend on actual state change.

## 5. Contract isolation

`contract.json` is a Contract Forge implementation detail.

Conceptual flow:

```text
raw contract
   ↓ ContractSourcePort
raw data
   ↓ ContractParserPort
NormalizedContract
   ↓
Forge engines
```

Only the concrete contract-format adapter may know physical details such as `$defs`, `$ref`, `oneOf` or custom contract annotations.

Semantic domain anchors needed by Forge services may be exposed through normalized semantic paths. They belong to the Forge contract adapter, not ADCM.

Do not build a second schema by mapping every contract field into application code.

## 6. Validation, requirements and discovery are separate

These answer different questions:

```text
formal validation
→ is the document valid?

formal/fillable requirements
→ what structurally needs a value?

requirement discovery
→ which current requirements should be exposed now?
```

Discovery is workflow/UX policy. It must not become final schema validity.

The full supported JSON Schema validator and deterministic rules are the authority for formal validity.

Schema interpretation details belong to Forge service documentation.

## 7. Enrichment

Enrichment belongs to Contract Forge.

- persistence is behind `EnrichmentRepositoryPort`;
- normalized matching/applicability belongs to `EnrichmentResolver`;
- storage adapters must not become the authority for runtime applicability;
- derived values must be recomputable from current state/context;
- user-entered values and derived values remain logically separate;
- changing a relevant user value must not leave stale derived values behind.

Do not duplicate global behavior per system when it can be expressed declaratively.

Detailed semantics live in `mcp-contract-forge/docs/enrichment.md`.

## 8. State and editing invariants

`valid=True` describes current formal validity. It is not a terminal workflow state.

Users must remain able to edit existing values after completion.

A state change must preserve:
- provenance and evidence;
- accepted user-value history;
- authority rules;
- structural safety;
- revalidation;
- recomputation of derived state.

A candidate must never silently destroy an existing container or structure.

Detailed ADCM state behavior lives in its service documentation.

## 9. Context MCP invariant

Adding another optional context MCP should normally require only:
- a bounded adapter/tool integration;
- evidence/context normalization;
- optional PydanticAI tool exposure.

It should not require redesigning the mandatory Forge stabilization loop.

If it does, review the boundary.

## 10. Ports and adapters

Create ports at real I/O or independent change boundaries.

Do not create a port for every internal helper.

Examples of legitimate boundaries include:
- contract source/parser;
- enrichment repository;
- discovery policy repository;
- Forge integration;
- LLM heuristics;
- context MCP integration;
- session persistence;
- logging/audit persistence;
- future file extraction.

## 11. Complexity escalation

Unexpected implementation complexity is a design signal.

Before adding substantial workaround logic, verify whether the complexity is caused by:
- an invalid or inconsistent input/contract/schema/configuration;
- an ambiguous or overly literal requirement;
- a supposedly immutable component that is actually defective;
- a boundary being used to compensate for an upstream problem;
- an implementation whose complexity is disproportionate to the domain rule.

If a simple requirement starts requiring significant special cases, duplicated logic, complex reconciliation or changes across unrelated components:

> **STOP before implementing the workaround.**

Report:
1. observed problem;
2. likely incorrect assumption or source;
3. workaround complexity;
4. smallest corrective alternative;
5. recommendation.

Protected or out-of-scope files should not be changed silently. They also should not be treated as infallible. If their defect forces disproportionate complexity elsewhere, escalate it.

## 12. Stop conditions

Stop and review before continuing if any of these appears:

- contract parsing or contract-specific schema semantics in ADCM;
- Python runtime imports across ADCM/Forge;
- hard-coded source-system/source-type branches in ADCM core;
- LLM state mutation or authority decisions;
- Forge conversation/session state;
- formal JSON Schema validation in ADCM;
- a contract-layout change propagating beyond the Forge adapter without changed normalized semantics;
- enrichment storage logic leaking into domain applicability decisions;
- a new context MCP requiring stabilization redesign;
- deployment-specific logic inside domain/application code;
- an orchestrator accumulating logic clearly owned by another service/domain component;
- a simple requirement requiring a disproportionately complex workaround.

## 13. Documentation boundaries

Architecture documentation records durable intent and boundaries. It must not duplicate generated repository inventories.

Use:
- `docs/architecture.md` for system shape and major flows;
- `docs/CURRENT_STATE.md` for concise current cross-service behavior;
- `docs/DECISIONS.md` for accepted architecture decisions;
- service docs for implementation semantics local to that service;
- `docs/generated/` only for mechanically generated navigation/impact;
- `docs/active-task/` for current implementation work;
- `docs/history/` for completed task/history material.

Do not copy the same rule into every document.

## 14. Final test

After every design change ask:

> **Does ADCM still understand the user while Contract Forge understands the contract?**

If not, redesign before implementation continues.
