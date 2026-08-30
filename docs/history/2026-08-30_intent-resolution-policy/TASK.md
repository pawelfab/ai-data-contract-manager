---
status: completed
created: 2026-08-30
type: fix
services:
  - ai-data-contract-manager
---

# Task: Intent resolution policy

## Problem

An intent resolver can classify a user message as a knowledge query while also
returning a spurious mutation candidate. `TurnOrchestrator` currently forwards
every resolver candidate to `CandidatePolicy`, so Session Audit may contain
`candidate.accepted` even though the user only asked for information and the
document ultimately remained unchanged.

## Goal

Introduce an explicit intent classification and a deterministic application
policy between the raw resolver output and `CandidatePolicy`. Knowledge-only
turns must never forward candidates to mutation evaluation, while mixed turns
must retain both the explicit mutation candidates and the knowledge query.

## Scope

Included:
- add a required intent kind to the raw `IntentResolution` contract;
- introduce a separate typed `EffectiveIntentResolution` contract;
- add an independently testable `IntentResolutionPolicy` application black box;
- preserve the raw resolver output in the `intent.resolved` audit event;
- pass only effective candidates to `CandidatePolicy`;
- update heuristic and PydanticAI intent resolver adapters;
- update affected test doubles, audit assertions and intent-resolution tests;
- document the new module contract and durable behavior.

## Out of scope

- changing same-value `SET` candidates into `candidate.ignored`;
- changing `CandidatePolicy` decision rules;
- changing `DocumentEngine`, provenance, mutation log or fixed-point behavior;
- changing Contract Forge or any cross-service wire contract;
- changing the public REST API;
- adding a general natural-language classifier to the bootstrap heuristic resolver.

## Constraints

- `IntentResolution` is raw resolver output and must not be mutated in place.
- `EffectiveIntentResolution` is the only resolution passed toward candidate evaluation.
- `KNOWLEDGE` clears candidates and preserves `knowledge_query`.
- `MUTATION` preserves candidates and clears `knowledge_query`.
- `MIXED` preserves both.
- Truly unrecognized heuristic input must remain unresolved and must not be
  mislabeled as a knowledge query merely because no mutation pattern matched.
- `CandidatePolicy` must not import or know `IntentKind`.
- Resolver inconsistency must fail safe without aborting the whole turn.
- No concrete contract paths or contract-version-specific models may be added to core.

## Acceptance criteria

- [x] A knowledge-only resolution with a spurious candidate produces no
      `candidate.accepted` event and no user mutation.
- [x] A mixed resolution still applies its explicit mutation candidate and keeps
      its knowledge query.
- [x] A mutation resolution forwards candidates and exposes no effective knowledge query.
- [x] Session Audit records the complete raw resolution, including `intent_kind`
      and any candidate suppressed by the policy.
- [x] `CandidatePolicy` remains unchanged and receives no intent classification.
- [x] Heuristic fallback does not automatically convert every unrecognized message
      into a knowledge query.
- [x] Focused and full ADCM regression tests pass.

## Relevant references

- issue/ticket: failing `test_knowledge_query_does_not_accept_same_value_candidate`
- prior task/decision: `docs/history/2026-08-29_compact-session-audit/`
- documentation: `docs/ARCHITECTURE_BASELINE.md`, `docs/CORE_INVARIANTS.md`,
  `docs/MODULE_CONTRACTS.md`, `docs/BUSINESS_BEHAVIOR.md`
