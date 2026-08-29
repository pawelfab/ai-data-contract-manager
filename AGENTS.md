# ADCM repository instructions

Before planning or implementation read:

1. docs/CURRENT_STATE.md
2. docs/ARCHITECTURE_BASELINE.md
3. docs/CORE_INVARIANTS.md
4. docs/MODULE_CONTRACTS.md
5. docs/BUSINESS_BEHAVIOR.md

Use:
- docs/generated/repository-map.md
- docs/generated/repository-inventory.json

before doing broad repository searches.

## Architecture boundaries

- ADCM owns conversation, session state, semantic resolution and orchestration.
- Contract Forge owns contract interpretation, deterministic validation and requirement discovery.
- No direct Python imports between services.
- ADCM must not contain concrete contract paths unless explicitly required by an adapter.
- LLM must not directly mutate ContractState.

## Working rules

Prefer:
1. repository map
2. targeted grep
3. reading individual files

Do not recursively inspect the entire repository unless necessary.

When implementation becomes substantially more complex than the requirement suggests,
stop and explain the architectural problem before introducing a workaround.

## Agent delegation policy

The main agent is the coordinator and final decision maker.

Use subagents to reduce main-agent context usage and avoid spending
high-capability reasoning on mechanical repository work.

### General rule

Do not use the main agent for work that can be safely delegated as a
small, bounded task.

Prefer:

- `explorer` for repository discovery
- `worker` for narrow implementation
- `reviewer` for independent verification

The main agent remains responsible for:
- understanding the user's actual requirement
- architecture decisions
- task decomposition
- resolving ambiguity
- deciding service boundaries
- integrating findings from multiple agents
- final acceptance of changes

Subagent output is evidence, not authoritative truth.

---

## Explorer

Delegate to `explorer` for:

- locating files
- finding classes, functions and methods
- grep/search
- finding references and call sites
- identifying tests
- inspecting repository structure
- reading repository-map.md / repository-inventory.json
- answering narrow questions about where functionality lives

Before broad repository search, prefer existing generated repository maps.

The main agent should not perform broad repository exploration itself
when the explorer can answer the question.

Give explorer narrow questions.

Good:

> Find where CandidateOutcome.changed is produced and consumed.
> Return file paths, symbols and relevant execution flow.

Bad:

> Understand the whole ADCM application.

---

## Worker

Delegate to `worker` only after the main agent understands the problem
and has determined the intended implementation boundary.

Use worker for:

- small isolated implementation
- mechanical code changes
- narrow refactors
- adding or modifying tests
- straightforward bug fixes
- repetitive changes with clear rules

Provide the worker:

- exact goal
- relevant files or symbols when known
- constraints
- expected behavior
- tests to run
- explicit non-goals

Do not delegate unresolved architecture decisions to worker.

If worker discovers that the change requires:
- new architecture
- cross-service responsibility changes
- large unexpected complexity
- violation of an architecture guardrail
- significant behavior not covered by the task

the worker must stop and return the problem to the main agent.

---

## Reviewer

For meaningful implementation changes, use an independent reviewer
after the worker finishes.

The reviewer must inspect actual code and tests rather than trusting
the worker handoff.

Reviewer should check:

- correctness
- regressions
- architecture boundaries
- unnecessary complexity
- missing edge cases
- missing tests
- unintended changes
- compliance with AGENTS.md and architecture guardrails

A worker must not review its own work.

For trivial mechanical edits, independent review may be skipped.

For architecture-sensitive changes, prefer a stronger reviewer.

---

## Delegation workflow

For non-trivial changes prefer:

1. Main agent understands the requirement.
2. Main agent reads relevant architecture/task documentation.
3. Delegate repository discovery to `explorer`.
4. Main agent determines the execution path and implementation plan.
5. Delegate bounded implementation to `worker` when appropriate.
6. Worker runs focused tests and returns a handoff.
7. Delegate independent verification to `reviewer`.
8. Main agent evaluates review findings.
9. Main agent resolves issues or delegates targeted fixes.
10. Main agent performs final verification.

Do not create subagents merely to increase parallelism.

Delegate when it:
- reduces main-agent context
- isolates a well-defined task
- saves expensive reasoning
- provides useful independent verification

---

## Context isolation

Give subagents the minimum context needed for their task.

Do not ask a subagent to read the entire repository when a repository
map, specific files or symbols are sufficient.

Prefer multiple narrow questions over one broad repository-analysis task.

The main agent should synthesize results from subagents rather than
passing large raw outputs between agents.

---

## Escalation

If a subagent cannot answer confidently with the provided context,
return the uncertainty to the main agent.

Do not compensate for missing understanding by inventing abstractions
or introducing complex workarounds.

When implementation complexity appears disproportionate to the
requirement, escalate before implementing the workaround.