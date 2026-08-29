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

## Architecture guardrails for coding agents

Before changing code, preserve these rules.

1. **One owner per responsibility.** Do not duplicate the same business decision across multiple modules.

2. **Prefer black boxes.** New functionality should expose a small typed input/output contract and hide implementation details.

3. **Core must not know infrastructure.** Domain/application code must not depend on MCP, FastAPI, BigQuery, filesystem, provider SDKs, or concrete transports.

4. **Ports describe capabilities, not technologies.** Prefer `SchemaExplorerPort`, `ContractForgePort`, `IntentResolverPort`; avoid generic `McpPort`, `HttpPort`, `BigQueryPort`.

5. **Adapters implement ports.** Technology-specific code belongs in adapters and should be replaceable without changing core.

6. **Services are independent.** ADCM and every MCP service have separate source trees, dependencies, virtual environments and containers. Never import Python code across services.

7. **Service boundaries use wire contracts.** Communicate through MCP/JSON/HTTP and map responses into local models.

8. **ADCM core must not know concrete contract structure.** Do not hard-code paths such as `sourceSystemGcpId`, `silver.tables`, `gold.entries`, source types, or specific sections when this knowledge can come from Forge or configuration.

9. **Treat the contract document as dynamic JSON.** Do not create ADCM domain models mirroring a particular `contract.json` version.

10. **Prefer configuration over branching.** System-specific behavior, path mappings, priorities, templates and conditions should be data-driven where an existing engine can express them.

11. **LLM interprets; deterministic code decides.** LLM may produce structured intent/candidates/advice. It must not directly mutate `ContractState`, decide authority, run fixed-point logic, or control mandatory Forge calls.

12. **Automatic values are proposals.** Forge enrichment/defaults and ADCM/user rules produce proposals, not direct mutations.

13. **All proposals pass through one authority mechanism.** Apply precedence and conflict resolution centrally before creating mutation commands.

14. **Only the mutation owner changes `ContractState`.** Do not modify the document directly from orchestrators, rules engines, adapters or LLM code.

15. **Orchestrators coordinate, not implement business rules.** If an orchestrator accumulates many `if/elif` branches, extract the responsibility into a dedicated module.

16. **Optional integrations must be fail-open unless explicitly required.** A disabled or unavailable Context MCP should produce `skipped/degraded`, not break the core workflow.

17. **Do not add a special case just to make a new test pass.** First classify whether the issue is a bug, missing configuration, adapter problem, missing abstraction, or wrong architecture boundary.

18. **Prefer extending over modifying.** For a new capability, prefer a new module/port/adapter over increasing the responsibilities of an existing large module.

19. **Keep blast radius small.** A normal feature should primarily affect its owner module, tests, and possibly one integration/composition point. Large cross-cutting edits require architectural review first.

20. **Use typed contracts between black boxes.** Prefer Pydantic models for stable inputs/outputs. Raw `dict[str, Any]` should be limited to intentionally dynamic data such as the contract document.

21. **Do not create abstractions without a concrete responsibility.** Avoid unnecessary Manager/Factory/Dispatcher/Processor layers. Simplicity is preferred.

22. **Every important module must be independently testable.** Unit tests should not require real MCP, FastAPI, BigQuery or LLM unless that integration itself is under test.

23. **Protect architecture with tests where practical.** Core should not import infrastructure packages or code from another service.

24. **Implementation changes must not silently change existing business behavior.** Run existing regression/use-case tests after every feature.

25. **Stop before overengineering.** If a local feature requires many new branches, broad core changes, or significant complexity, report the missing abstraction and propose a simpler design before continuing.

### Before implementing a non-trivial feature

Provide a short plan containing:

* owner module,
* new black boxes,
* input/output contracts,
* ports added or changed,
* adapters added,
* existing modules touched,
* core impact,
* risks,
* tests.

If the list of existing modules touched is large, reconsider the design before coding.

### Final rule

Optimize for:

```text
correct behavior
+ clear ownership
+ stable interfaces
+ small change impact
+ easy future extension
```

Do not optimize only for making the current test green.


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