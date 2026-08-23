# ADCM — mandatory instructions for coding agents

This file defines how coding agents work in this repository.

The authoritative architecture contract is:

`docs/architecture-guardrails.md`

## 1. Read before changing code

Always read:

1. `docs/architecture-guardrails.md`
2. `docs/CURRENT_STATE.md`
3. the current task under `docs/active-task/<task>/`
4. the relevant service `docs/architecture.md`
5. the actual code and tests that implement the affected behavior

Then read only documentation relevant to the task.

### Read conditionally

Architecture or ownership change:
- `docs/architecture.md`
- `docs/DECISIONS.md`

Known limitation or regression:
- `docs/KNOWN_ISSUES.md`

ADCM state, stabilization, semantic resolution or LLM behavior:
- `ai-data-contract-manager/docs/contract-state.md`
- `ai-data-contract-manager/docs/session-flow.md`
- `ai-data-contract-manager/docs/llm-heuristics.md`

Contract parsing, schema, requirements, discovery, arrays or unions:
- `mcp-servers/mcp-contract-forge/docs/contract-format.md`
- `mcp-servers/mcp-contract-forge/docs/requirement-discovery.md`

Enrichment:
- `mcp-servers/mcp-contract-forge/docs/enrichment.md`

Rules:
- `mcp-servers/mcp-contract-forge/docs/rules-engine.md`

Ports, adapters or transport:
- the relevant service `docs/ports-and-adapters.md`
- Forge `docs/mcp-api.md` when MCP protocol/transport changes

Deployment, logging or documentation tooling:
- the corresponding specialized document

Historical rationale:
- `docs/history/`
- service `CHANGELOG.md`
- service `docs/history/`

Do not load unrelated documentation by default.

## 2. Generated repository documentation

`docs/generated/` contains deterministic navigation aids, not architecture authority.

Use:
- `docs/generated/repository-map.md` to locate files/classes/functions;
- `docs/generated/repository-inventory.json` for machine-readable repository inventory;
- `docs/generated/documentation-impact.md` to identify curated documentation that may require review.

Do not read the complete generated repository map unless necessary. Inspect only the relevant sections and then verify behavior in actual code and tests.

Generated files never replace curated architecture or service documentation.

## 3. Core invariant

> **ADCM understands the user. Contract Forge understands the contract.**

If a proposed change makes this false, stop and redesign.

## 4. Non-negotiable boundaries

- No runtime Python imports between ADCM and Contract Forge.
- ADCM does not parse or interpret `contract.json`, JSON Schema structure or contract DSL details.
- Contract Forge does not own conversation/session state or LLM semantic interpretation.
- Contract Forge is a mandatory deterministic dependency, not an optional LLM-selected tool.
- Context MCPs provide context/evidence/actions and do not mutate `ContractState`.
- LLM output is a proposal. Only deterministic ADCM application logic mutates `ContractState`.
- Formal validation remains separate from requirement discovery.
- Derived values are recomputable and must not silently override accepted user values.
- `valid=True` does not lock the session; existing values remain editable.

## 5. Complexity escalation

Unexpected complexity is a signal to investigate assumptions before adding code.

If a simple requirement starts requiring substantial workaround logic, many special cases, cross-component changes or non-obvious transformations:

1. stop before introducing that complexity;
2. identify which input, requirement, schema, configuration or assumption caused it;
3. compare the workaround with the smallest corrective alternative;
4. report the inconsistency before continuing with a disproportionate workaround.

A file marked `do not modify` or `out of scope` must not be silently changed, but it also must not force arbitrary downstream complexity when it appears defective. Escalate the inconsistency.

## 6. Task documentation

Every feature, fix or material refactor must have a task directory:

`docs/active-task/YYYY-MM-DD_task-name/`

Use:
- `TASK.md` — problem, goal, scope and acceptance criteria;
- `IMPLEMENTATION.md` — implementation plan, findings, decisions, tests and final result.

During implementation, update `IMPLEMENTATION.md` when:
- scope materially changes;
- an assumption proves wrong;
- unexpected complexity is discovered;
- the final implementation differs from the approved plan.

Do not use it as a minute-by-minute log.

After the task is complete:
1. run relevant tests and quality gates;
2. review `docs/generated/documentation-impact.md`;
3. update only curated documentation whose responsibility or documented behavior actually changed;
4. record the final result and unresolved items in `IMPLEMENTATION.md`;
5. set the task status to completed;
6. move the entire directory unchanged to `docs/history/YYYY-MM-DD_task-name/`.

Completed tasks must not remain under `docs/active-task/`.

## 7. Before implementation

For a non-trivial task, `IMPLEMENTATION.md` must state:

```text
Owning service:
Owning boundary:
Files expected to change:
Files/services not to change:
Main invariant:
Implementation approach:
Tests:
Architecture risks:
```

## 8. Before completion

Do not declare a code-changing task complete until:
- relevant tests pass;
- quality gates required by the repository pass;
- documentation freshness has been reviewed;
- unexpected findings are resolved or explicitly recorded;
- required curated documentation is updated;
- the task directory is moved from `docs/active-task/` to `docs/history/`.

Prefer the smallest local change that preserves the architecture.
