# Multi-agent repository rules

## Source-of-truth order

1. Executable code and database migrations.
2. Automated tests and observable command output.
3. Public interfaces and schemas.
4. `docs/architecture/generated/repository-map.md`.
5. Curated files in `docs/architecture/`.
6. Change contracts.
7. Assumptions.

Never present an assumption as a confirmed repository fact.

## Request modes

Classify every request before acting:

- `EXPLAIN`: explain current behavior; do not edit files.
- `PLAN`: produce a reviewed implementation contract; do not edit application code.
- `IMPLEMENT`: edit code only when the user explicitly asks to implement, modify, fix, or refactor.
- `DOC_SYNC`: update architecture documentation to match existing code.
- `BOOTSTRAP_DOCS`: build the initial repository knowledge base.

Do not infer `IMPLEMENT` from a request to discuss, explain, compare, estimate, design, or plan.

## Delegation

- The Feature Coordinator is the only orchestration agent.
- Worker agents must not invoke other agents.
- Delegate isolated analysis when it keeps the parent context smaller.
- Return summaries and evidence, not entire files.
- For more than two independent modules, Code Verifier tasks may run in parallel.
- Maximum correction loops:
  - architecture/final contract: 1 review cycle,
  - implementation/review: 2 correction cycles.
- Stop and report unresolved blockers rather than looping indefinitely.

## Repository knowledge

Before broad code search:
1. Read `docs/architecture/README.md`.
2. Read `docs/architecture/.freshness.json` if present.
3. Read the relevant module, flow, and symbol documents.
4. Read `docs/architecture/generated/repository-map.md`.
5. Inspect code only for the requested scope or to verify stale/missing facts.

Every factual answer about code must name relevant paths and symbols. Use line numbers when the available tooling returns stable line information.

## Symbol discipline

- Confirm every existing class, method, function, endpoint, event, table, and configuration key in the repository.
- Mark proposed symbols as `NEW`.
- Do not create a parallel abstraction when an existing project pattern can be extended.
- Do not propose an interface solely to satisfy a pattern; state the concrete boundary it protects.
- Specify callers, callees, error paths, side effects, transaction boundaries, and tests.

## Change contracts

A final contract belongs in:

`docs/architecture/contracts/<feature-slug>.md`

It must contain:
- scope and non-goals,
- confirmed current behavior,
- proposed flow,
- exact file and symbol changes,
- method/function signatures,
- models and schemas,
- errors and compatibility,
- migrations,
- tests and quality gates,
- implementation order,
- risks,
- assumptions and open decisions,
- acceptance criteria,
- symbol change registry.

## Implementation

- Implement only from a final reviewed contract.
- Keep changes inside the contract unless a deviation is required by repository facts.
- Record each deviation with reason and impact.
- Add or update tests with behavior changes.
- Run configured formatting, linting, type checking, tests, and build commands.
- Never hide failing tests.
- Never weaken tests merely to make a build green.

## Documentation completion rule

After application code changes, invoke Docs Updater when any of these changed:
- externally observable behavior,
- module responsibility or dependency,
- class/function contract,
- endpoint, event, schema, migration, or data flow,
- error handling or transaction boundary,
- operational command or configuration.

Docs Updater must:
1. inspect the final diff and tests,
2. update only impacted documentation,
3. regenerate repository inventory,
4. run `doc_freshness.py --mark-current`,
5. report updated documentation paths.

Code changes are incomplete until this rule is satisfied or the agent explicitly states why documentation is unaffected.
