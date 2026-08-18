# Repository agent workflow rules

## Source-of-truth order

1. Executable code and database migrations.
2. Automated tests and observable command output.
3. Public interfaces and schemas.
4. `docs/architecture/generated/repository-map.md` as navigation assistance.
5. Curated files in `docs/architecture/`.
6. Change contracts.
7. Assumptions.

Never present an assumption as a confirmed repository fact.

## Available workflows

- `EXPLAIN`: explain current behavior; do not edit files.
- `PLAN_FAST`: one-agent planning; no subagents and no application-code edits.
- `PLAN_PREVIEW`: one-agent planning returned only in chat; no file edits.
- `PLAN_REVIEWED`: reviewed multi-agent planning; no application-code edits.
- `IMPLEMENT_FAST`: one-agent implementation, tests, self-review, and documentation synchronization.
- `IMPLEMENT_REVIEWED`: reviewed contract-first multi-agent implementation.
- `REVIEW_ONLY`: independent review of an existing diff; no file edits.
- `DOC_SYNC`: synchronize architecture documentation to existing code.
- `BOOTSTRAP_DOCS`: create the initial repository knowledge base.

An explicit mode or a prompt file's selected agent takes priority. Never infer implementation from a request to explain, discuss, compare, estimate, design, or plan.

## Command routing

| Command | Agent/workflow | Subagents |
|---|---|---|
| `/explain-current` | Feature Coordinator / `EXPLAIN` | Repository Guide; optional Code Verifier |
| `/plan-change-preview` | Planner Fast | none |
| `/plan-change` | Planner Fast | none |
| `/plan-change-reviewed` | Feature Coordinator / `PLAN_REVIEWED` | full reviewed planning chain |
| `/implement-change` | Feature Fast | none |
| `/implement-change-reviewed` | Feature Coordinator / `IMPLEMENT_REVIEWED` | full reviewed implementation chain |
| `/review-current-change` | Feature Coordinator / `REVIEW_ONLY` | Implementation Reviewer only |
| `/sync-architecture-docs` | Feature Coordinator / `DOC_SYNC` | bounded verifier and Docs Updater |
| `/bootstrap-repository-knowledge` | Feature Coordinator / `BOOTSTRAP_DOCS` | bounded parallel verification and Docs Updater |

## Workflow selection

Use fast workflows for ordinary, bounded work.

Prefer reviewed workflows when a change affects:

- authentication or authorization,
- secrets or permissions,
- database migrations or destructive data operations,
- transaction boundaries or concurrency,
- public API compatibility,
- cross-module architecture,
- security-sensitive integrations,
- large refactoring or a difficult-to-review diff.

Do not silently upgrade a fast request to a reviewed workflow. Complete the selected workflow and recommend the reviewed variant when justified.

## Delegation

- Feature Coordinator is the only orchestration agent.
- Planner Fast and Feature Fast do not expose the `agent` tool and must not invoke subagents.
- Worker agents must not invoke other agents.
- Pass summaries and evidence, not whole files or full chat history.
- Parallelize only independent verification scopes.
- Maximum loops:
  - contract review: one cycle,
  - implementation correction/review: two cycles.
- Stop and report unresolved blockers rather than looping indefinitely.

## Repository knowledge

Before broad search:

1. Read `docs/architecture/README.md`.
2. Read `docs/architecture/.freshness.json` or run the freshness command.
3. Read relevant module, flow, symbol, and contract documents.
4. Use `docs/architecture/generated/repository-map.md` to navigate.
5. Inspect only the requested source scope or stale/missing facts.

Every factual answer about code should name relevant paths and symbols. Use line numbers only when tooling provides stable line information.

## Symbol discipline

- Confirm every existing class, method, function, endpoint, event, table, and configuration key.
- Mark proposed symbols as `NEW`.
- Extend existing project patterns instead of creating parallel abstractions.
- Do not introduce an interface without stating the concrete boundary it protects.
- Specify callers, callees, errors, side effects, transaction ownership, idempotency, concurrency, and tests where relevant.

## Change contracts

Contracts live in:

`docs/architecture/contracts/<feature-slug>.md`

Statuses:

- `FAST_PLAN`: produced by fast planning; not independently reviewed.
- `DRAFT`: intermediate reviewed plan.
- `FINAL`: independently reviewed and implementable.
- `BLOCKED`: unresolved blocker remains.

A complete contract contains:

- scope and non-goals,
- confirmed current behavior,
- proposed flow,
- exact file and symbol changes,
- signatures and contracts,
- models, schemas, endpoints, events, and migrations,
- errors, compatibility, transactions, concurrency, and idempotency,
- tests and quality gates,
- implementation order,
- risks, assumptions, and open decisions,
- acceptance criteria,
- symbol change registry.

`IMPLEMENT_FAST` may use a matching contract but does not require a reviewed `FINAL` contract. `IMPLEMENT_REVIEWED` requires `STATUS: FINAL`.

## Implementation

### Fast

- Feature Fast performs focused analysis, implementation, tests, self-review, and documentation updates directly.
- It must not invoke subagents.
- It must not label self-review as independent review.

### Reviewed

- Implement from a current `FINAL` contract.
- Implementer changes code and tests.
- A separate Implementation Reviewer reviews the complete diff.
- Docs Updater synchronizes architecture documentation after the final implementation.

### Shared rules

- Inspect the current diff before editing.
- Keep changes inside requested scope.
- Add tests with behavior changes.
- Run configured relevant checks.
- Never hide failures or weaken tests merely to pass checks.
- Preserve public compatibility unless explicitly authorized.

## Documentation completion rule

After application source changes, update architecture documentation when any of these changed:

- externally observable behavior,
- module responsibility or dependency,
- class/function contract,
- endpoint, event, schema, migration, or data flow,
- error handling or transaction boundary,
- operational command or configuration.

Completion procedure:

1. Run `python scripts/agent/doc_impact.py --working-tree`.
2. Inspect final code, diff, callers, and tests.
3. Update only impacted curated files under `docs/architecture/`.
4. Run `python scripts/agent/repo_inventory.py`.
5. Run `python scripts/agent/doc_freshness.py --mark-current --reason "<specific reason>"`.
6. Run `python scripts/agent/doc_freshness.py --check`.

The freshness script refuses to mark changed source as current when curated documentation did not change, unless the agent explicitly uses `--allow-no-doc-change` with a specific rationale. Use that exception only when the change has genuinely no documentation impact.

Code-changing work is incomplete until documentation is synchronized or the no-impact exception is explicitly justified.

## Repository-specific ADCM rules

- Product: AI Data Contract Manager (ADCM), a schema-authoritative conversational orchestrator for building data-contract drafts around MCP capabilities.
- Runtime: Python 3.11 or newer; package metadata and pytest configuration live in `pyproject.toml`.
- Source root: `src/adcm`; tests: `tests`; authoritative contract artifacts: `contracts` and `examples/contract-rules.json`.
- Architecture: domain and application code depend on ports; adapters implement ports. Keep `src/adcm/domain` independent of Pydantic AI, MCP transports, persistence, and web frameworks.
- Read `LLM_REPO_GUIDE.md` before changing application behavior. Its invariants are repository constraints, especially:
  - Contract Forge owns legal schema paths, workflow order, requirements, defaults, enrichments, and validation.
  - LLM and external MCP output never mutate `ContractDraft` directly.
  - `DraftProjector.project` accepts only resolved values whose paths are currently authorized.
  - `CandidateResolver.resolve` selects values deterministically; historical state is superseded rather than deleted.
- There is no database-migration root or deployment manifest in the current repository. Do not invent one.
