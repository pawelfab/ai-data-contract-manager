---
status: completed
created: 2026-08-30
type: fix
services:
  - ai-data-contract-manager
---

# Task: Complete the unresolved intent contract

## Problem

`IntentKind.UNRESOLVED` already exists and prevents mutation candidates from
reaching mutation evaluation, but the four-kind contract is not yet fully
enforced. Knowledge and mixed results may omit their required knowledge query,
unresolved results may omit an explanation, and `ResponseComposer` does not know
the effective intent kind. Consequently an unresolved turn can finish with a
normal contract-status/YAML response instead of asking the user to clarify.

## Goal

Make the four intent kinds deterministic and observable end to end. Invalid raw
resolver combinations must degrade safely to effective `UNRESOLVED`, no
user-candidate mutation may be attempted, and the user must receive a clear
request to clarify while the existing structured `unresolved` details remain
available through the API.

## Scope

Included:
- enforce the complete intent matrix in `IntentResolutionPolicy`;
- require a non-blank effective `knowledge_query` for `KNOWLEDGE` and `MIXED`;
- ensure effective `UNRESOLVED` contains at least one reason;
- degrade inconsistent raw knowledge/mixed results to effective `UNRESOLVED`;
- carry effective `intent_kind` in internal `TurnOutcome`;
- make `BasicResponseComposer` return a clarification message for `UNRESOLVED`;
- align the PydanticAI prompt with the complete matrix;
- add policy, orchestration, response and API regression tests;
- synchronize curated architecture and business documentation.

## Out of scope

- exposing `intent_kind` as a new public REST response field;
- changing `CandidatePolicy` or same-value candidate behavior;
- skipping required Forge stabilization or external checks;
- changing Contract Forge, document mutation, provenance or fixed-point logic;
- adding a general natural-language classifier to the heuristic resolver.

## Constraints

- Raw `IntentResolution` remains unchanged and fully auditable.
- Cross-field inconsistencies are handled by deterministic application policy,
  not by a Pydantic model validator that rejects an imperfect LLM result.
- `MUTATION`: candidates allowed, effective `knowledge_query=None`, unresolved optional.
- `KNOWLEDGE`: candidates ignored, non-blank knowledge query required, unresolved optional.
- `MIXED`: candidates allowed, non-blank knowledge query required, unresolved optional.
- `UNRESOLVED`: candidates ignored, effective `knowledge_query=None`, at least one
  unresolved item with a non-blank reason.
- Inconsistent `KNOWLEDGE` or `MIXED` output fails safe as effective `UNRESOLVED`.
- `CandidatePolicy` does not know `IntentKind`.
- Public API shape remains unchanged.

## Acceptance criteria

- [x] Every effective intent satisfies the four-row matrix.
- [x] Missing knowledge query for raw `KNOWLEDGE` or `MIXED` becomes effective
      `UNRESOLVED` with a deterministic reason and no candidates.
- [x] Raw `UNRESOLVED` without a reason receives a deterministic effective reason.
- [x] Raw resolution remains unchanged and is recorded in `intent.resolved`.
- [x] An unresolved turn does not invoke `CandidatePolicy` and produces no user
      mutation or `candidate.accepted` event.
- [x] An unresolved turn returns a message beginning with
      `Nie udało mi się jednoznacznie zrozumieć`.
- [x] Existing `unresolved` details remain present in the REST response.
- [x] Mutation, knowledge and mixed regression behavior remains unchanged.
- [x] Full ADCM test suite passes.

## Relevant references

- issue/ticket: follow-up to the intent-resolution policy implementation
- prior task/decision: `docs/history/2026-08-30_intent-resolution-policy/`
- documentation: `docs/ARCHITECTURE_BASELINE.md`, `docs/CORE_INVARIANTS.md`,
  `docs/MODULE_CONTRACTS.md`, `docs/BUSINESS_BEHAVIOR.md`
