---
status: completed
created: 2026-08-30
completed: 2026-08-30
---

# Implementation: Complete the unresolved intent contract

## Implementation contract

Owning service:

`ai-data-contract-manager`

Owning boundary:

The application boundary from raw intent resolution through effective intent
normalization and the internal response-composition input.

Files expected to change:
- `ai-data-contract-manager/src/adcm/application/intent_resolution_policy.py`
- `ai-data-contract-manager/src/adcm/domain/turn.py`
- `ai-data-contract-manager/src/adcm/application/turn_orchestrator.py`
- `ai-data-contract-manager/src/adcm/adapters/response_basic.py`
- `ai-data-contract-manager/src/adcm/adapters/intent_pydantic_ai.py`
- focused policy, turn, response and API tests
- curated documentation describing intent and response behavior

Files/services explicitly not to change:
- `ai-data-contract-manager/src/adcm/application/candidate_policy.py`
- `ai-data-contract-manager/src/adcm/application/document_engine.py`
- public REST DTOs and mappers
- stabilization, proposal reconciliation and provenance behavior
- `mcp-servers/mcp-contract-forge/`

Main invariant:

Only a coherent `EffectiveIntentResolution` controls orchestration and response
composition; raw resolver output remains unchanged and auditable.

Implementation approach:

Keep Pydantic structural validation permissive enough to accept imperfect raw
LLM combinations. Extend the existing application policy to enforce the complete
matrix and synthesize user-safe unresolved reasons when required. Add effective
`intent_kind` to internal `TurnOutcome`, set it in the orchestrator and let the
basic response adapter short-circuit to a clarification response for unresolved
turns. Do not expose the enum through REST.

Tests:
- table-driven unit tests for every valid and inconsistent policy combination;
- raw-model immutability tests;
- unresolved orchestration test proving no accepted candidate or mutation;
- basic response test for the clarification message;
- API test preserving structured unresolved details;
- complete ADCM pytest suite.

Architecture risks:
- Degrading malformed `MIXED` to `UNRESOLVED` suppresses otherwise plausible
  candidates. This is intentional fail-safe behavior because the raw contract is
  internally inconsistent and LLM output cannot authorize mutation by itself.
- Adding required internal `TurnOutcome.intent_kind` requires deliberate updates
  to every test constructor but does not change public DTOs.
- The clarification message must not accidentally include YAML from an unchanged,
  otherwise complete contract.

## Current behavior

The enum, effective model, heuristic unresolved fallback and candidate suppression
already exist. The policy does not require knowledge queries or unresolved reasons.
`TurnOutcome` contains only the unresolved detail list, and `BasicResponseComposer`
ignores it, so unresolved turns receive the normal status/diagnostic/YAML response.

## Planned changes

1. Complete deterministic policy validation and fail-safe degradation.
2. Skip candidate evaluation for effective unresolved intent and carry effective
   intent kind into internal turn output.
3. Compose an explicit clarification response for unresolved turns.
4. Tighten PydanticAI instructions and add focused regression coverage.
5. Synchronize curated documentation and run all verification gates.

## Unexpected findings

None.

### Complexity escalation rule

Unexpected complexity is a signal to re-check assumptions before adding code.

If a simple requirement begins to require substantial workaround logic, many
special cases, non-obvious transformations or changes across unrelated components,
stop before implementing that complexity and record the finding here.

Do not silently compensate for a likely defect in an input, contract, schema,
configuration or protected file.

## Deviations from the original plan

None.

## Verification

- [x] relevant unit tests pass
- [x] relevant integration tests pass — full ADCM suite: 74 passed
- [x] architecture/boundary tests pass when applicable
- [x] configured quality gates pass — `git diff --check` clean
- [x] documentation freshness reviewed
- [x] `docs/generated/documentation-impact.md` reviewed
- [x] required curated documentation updated

## Final result

The existing four-value intent enum now has a complete deterministic effective
contract. `IntentResolutionPolicy` preserves valid mutation/knowledge/mixed
results, clears forbidden channels, degrades knowledge or mixed results with a
missing query to `UNRESOLVED`, and guarantees that effective unresolved details
contain an actual non-blank string reason. Raw resolver output remains unchanged
and is audited before policy application.

`TurnOutcome` now carries the effective internal intent kind. The orchestrator
does not invoke `CandidatePolicy` for effective `UNRESOLVED`, emits the effective
unresolved details and continues mandatory stabilization. `BasicResponseComposer`
returns a clarification request without status or YAML, while the existing REST
response continues to expose structured unresolved details without adding a
public `intent_kind` field.

The PydanticAI prompt describes all four rows consistently. Focused policy,
orchestration, response and API tests cover malformed output, raw audit
preservation, skipped candidate evaluation and user-facing clarification. The
complete ADCM suite passed with 74 tests, `git diff --check` passed, and independent
review reported no remaining findings.

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
