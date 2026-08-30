---
status: completed
created: 2026-08-30
completed: 2026-08-30
---

# Implementation: Intent resolution policy

## Implementation contract

Owning service:

`ai-data-contract-manager`

Owning boundary:

The internal `IntentResolverPort` output boundary and the application-layer
coordination immediately before `CandidatePolicy`.

Files expected to change:
- `ai-data-contract-manager/src/adcm/domain/turn.py`
- `ai-data-contract-manager/src/adcm/application/intent_resolution_policy.py`
- `ai-data-contract-manager/src/adcm/application/turn_orchestrator.py`
- `ai-data-contract-manager/src/adcm/adapters/intent_heuristic.py`
- `ai-data-contract-manager/src/adcm/adapters/intent_pydantic_ai.py`
- focused tests that construct or serialize `IntentResolution`
- `docs/MODULE_CONTRACTS.md`
- `docs/BUSINESS_BEHAVIOR.md` if documentation impact requires a behavior clarification

Files/services explicitly not to change:
- `ai-data-contract-manager/src/adcm/application/candidate_policy.py`
- `ai-data-contract-manager/src/adcm/application/document_engine.py`
- provenance, proposal reconciliation and stabilization behavior
- `mcp-servers/mcp-contract-forge/`
- public REST DTOs and routes

Main invariant:

Only candidates authorized by deterministic `IntentResolutionPolicy` may reach
`CandidatePolicy`; raw resolver output remains unchanged and auditable.

Implementation approach:

Add `IntentKind` to raw resolution, add a distinct effective resolution model,
and implement a pure application policy with an explicit intent-kind matrix.
Audit the raw model first, then evaluate only effective candidates. Update both
resolver adapters to populate the required structured field. Keep PydanticAI as
the interpreting adapter and deterministic Python as the mutation gate.

Tests:
- unit matrix tests for `IntentResolutionPolicy`;
- knowledge-only, mixed and mutation orchestrator tests;
- heuristic resolver classification and unresolved fallback tests;
- compact/full audit payload tests;
- existing API and turn-audit tests using deterministic fakes;
- complete ADCM pytest suite.

Architecture risks:
- A false `KNOWLEDGE` classification suppresses a legitimate mutation. Raw audit,
  explicit prompt instructions and mixed-intent tests make this diagnosable.
- The existing three-value intent taxonomy does not describe a truly unresolved
  heuristic input. The implementation must preserve an explicit fail-safe
  unresolved path without mislabeling it as knowledge.
- Adding a required structured-output field breaks every constructor until all
  adapters and test doubles are deliberately updated; this is intentional.

## Current behavior

`IntentResolution` contains candidates, an optional knowledge query and unresolved
items but no explicit relationship between them. `TurnOrchestrator.run_turn`
audits the resolution and unconditionally passes all candidates to
`CandidatePolicy.evaluate`. The heuristic resolver treats every unmatched message
as `knowledge_query`. The PydanticAI prompt asks only for mutation candidates and
does not distinguish knowledge-only and mixed intent.

## Planned changes

1. Add required intent classification and a separate effective resolution type.
2. Implement deterministic normalization without changing the raw model.
3. Audit raw resolution, then use only effective candidates in the orchestrator.
4. Update heuristic and PydanticAI resolvers to return the expanded contract.
5. Update constructors, audit expectations, focused tests and module documentation.
6. Run focused tests, full regression and independent review.

## Unexpected findings

### Finding: unresolved input is outside the three-channel matrix

Observation:

The heuristic resolver has an existing unmatched-input branch, while
`MUTATION`, `KNOWLEDGE` and `MIXED` describe only recognized mutation/knowledge
channels.

Affected assumption:

A required three-value `intent_kind` alone was assumed to cover every existing
resolver result.

Implementation impact:

The resolver contract needs an explicit fail-safe representation for unresolved
input, or the heuristic would continue to misclassify every unknown message as
knowledge.

Workaround complexity:

Forcing unresolved input into one of the three recognized kinds would be a small
code workaround but would make the semantic contract false.

Simpler corrective option:

Represent unresolved intent explicitly and have the policy expose neither
candidates nor a knowledge query for it.

Decision:

Use an explicit unresolved intent kind only for the existing unresolved fallback;
keep the requested mutation/knowledge/mixed matrix unchanged.

## Deviations from the original plan

None.

## Verification

- [x] relevant unit tests pass — focused suite: 41 passed
- [x] relevant integration tests pass — full ADCM suite: 63 passed
- [x] architecture/boundary tests pass when applicable
- [x] configured quality gates pass — `git diff --check` clean
- [x] documentation freshness reviewed
- [x] `docs/generated/documentation-impact.md` reviewed
- [x] required curated documentation updated

## Final result

ADCM now models resolver output as required, raw `IntentResolution` with an
explicit `IntentKind`. A pure `IntentResolutionPolicy` creates a separate
`EffectiveIntentResolution` and applies the deterministic mutation/knowledge
matrix before candidate evaluation. `TurnOrchestrator` audits raw output before
the policy and sends only effective candidates to the unchanged
`CandidatePolicy`.

The heuristic resolver recognizes a narrow knowledge-query form and maps other
unknown input to fail-safe `UNRESOLVED`. The PydanticAI structured-output prompt
defines mutation, knowledge, mixed and unresolved intent and prohibits deriving
mutation candidates from questions or current document values. A spurious
candidate in a knowledge-only result remains visible in `intent.resolved` but is
never accepted or applied.

Focused tests passed (41), the complete ADCM suite passed (63), and independent
review reported no findings. Same-value candidate behavior was intentionally not
changed.

## Unresolved items

- none

## Completion procedure

Before declaring this task complete:

1. run relevant tests and repository quality gates;
2. verify documentation freshness;
3. review `docs/generated/documentation-impact.md`;
4. update only curated documents whose responsibility or documented behavior changed;
5. record the final implementation result, deviations and unresolved items above;
6. change this document metadata to:

```yaml
status: completed
completed: YYYY-MM-DD
```

7. update `TASK.md` status to `completed`;
8. move the entire task directory from:

`docs/active-task/YYYY-MM-DD_task-name/`

to:

`docs/history/YYYY-MM-DD_task-name/`

Do not leave completed task documentation in `docs/active-task/`.
