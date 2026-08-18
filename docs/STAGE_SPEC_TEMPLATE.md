# Stage specification template

Every implementation stage must be a separate file under `docs/implementation/` and must be written as an implementation contract, not as code.

## Goal
Describe the repository state that must exist after the stage. Focus on the outcome, not merely "create classes X/Y".

## Why this stage exists
State the problem this stage solves and why it is isolated from later work.

## Preconditions
List assumptions that must already be true. If an implementer finds a precondition false, they must stop and report it rather than silently work around it.

## Scope
Exact responsibilities included in this stage.

## Out of scope / Do not do
Concrete forbidden work, especially tempting adjacent tasks. Example: do not add UI, do not call Schema Explorer directly from Forge, do not move contract rules into ADCM, do not create a stateful Forge session.

## Architectural boundaries
State who owns what for this stage: ADCM / Forge / LLM / external MCP / DAG Generator.

## Invariants
List only the global invariants relevant to this stage plus stage-specific invariants.

## Files affected
| File | Action | Purpose |
|---|---|---|
| path | NEW/MODIFY/DELETE | reason |

## Public contracts
Describe Protocols, Pydantic models, enums and public methods. Public signatures are allowed; private method designs are not required.

## Inputs and outputs
Define typed request/response structures where the boundary is stable. Avoid untyped bags unless the content is inherently dynamic.

## State ownership
Explicitly state which component owns persistent/transient state and what must not cross the boundary.

## Data flow
Provide a short ASCII flow for the stage.

## Required behavior
Describe deterministic behavior and ordering constraints. Explain HOW at the contract level, not private algorithm details.

## Forbidden implementation shortcuts
List shortcuts that would make tests pass while violating architecture, e.g. relaxing Evidence invariants, accumulating allowed paths, UUID tie-breakers, fabricating provenance, rendering YAML after every Forge call.

## Error semantics
Define configuration, validation, dependency, capability, transport and application failures that matter in this stage.

## Status semantics
If workflow-related, use the canonical enums from `docs/MCP_CONTRACT.md`.

## Schema revision semantics
If Forge/render-related, define expected/current revision behavior and mismatch handling.

## Rendering semantics
If applicable: DRAFT/FINAL, final-validation precondition, stabilization timing, cache key.

## Template semantics
If applicable: Forge resolves `{...}` enrichment placeholders only and preserves runtime `{{...}}` DSL.

## Arrays and paths
If applicable: distinguish schema wildcard paths and concrete instance paths; preserve nested draft shape.

## Value precedence
If applicable: ADCM origin precedence vs Forge internal rule priority. Never assign that decision to LLM.

## Tests
Separate unit, integration, contract and negative tests. For every important test say what invariant it protects.

## Acceptance criteria
Objective verifiable completion criteria. Avoid "good quality" statements.

## Explicit non-goals
Repeat the most important things intentionally deferred to later stages.

## Documentation updates
List docs that must be updated when implementation is complete.

## Completion checklist
- implementation complete
- all relevant tests pass
- invariants reviewed
- docs updated
- no out-of-scope changes
- assumptions for next stage reviewed
