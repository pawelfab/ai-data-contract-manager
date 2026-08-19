---
module: application
source_roots:
  - src/adcm/application
last_verified: working-tree-2026-08-19
owners: []
---

# Application module

## Responsibility

Coordinate semantic interpretation, state mutation, candidate generation/resolution, stateless Contract Forge evaluation, external capability routing, draft projection, persistence, and canonical rendering.

## Public entry points

| Path | Symbol | Contract |
|---|---|---|
| `src/adcm/application/chat_service.py` | `ChatService.handle_user_message` | Load/create state, interpret a user turn, apply it, fast-forward until stable, persist, and return `(ConversationState, WorkflowOutcome)`. |
| `src/adcm/application/workflow_runner.py` | `WorkflowRunner.run_until_stable` | Deterministic Forge loop producing `WAITING_FOR_USER`, `BLOCKED_EXTERNAL`, `COMPLETE`, `INVALID`, or `FAILED`. |
| `src/adcm/application/render_service.py` | `ContractRenderService.render` | Cache rendering by draft hash, schema revision, and mode; guard FINAL rendering with a matching VALID receipt. |
| `src/adcm/application/capability_router.py` | `CapabilityRouter.register`, `execute` | Select the longest registered capability prefix or raise `KeyError`. |

## Internal flow and side effects

`TurnProcessor` appends message evidence and revisions but never edits the draft. `SignalBinder` and `PreferenceExpander` produce candidates only for concrete paths in the current schema view; an absent or ambiguous current binding resets a signal to `unbound`. `CandidateResolver` preflights every ID and confidence value, computes every per-path winner, and builds all resolutions before committing candidate statuses. Ranking uses origin precedence, same-origin Forge priority, correction revision/sequence, and confidence without UUID ordering; a policy-rank tie after confidence is rejected without partial status mutation. `DraftProjector` rebuilds the nested draft. `WorkflowRunner` stores capability results and Forge evidence. `ChatService` owns session persistence.

## Error and stability behavior

- An unavailable required capability yields `BLOCKED_EXTERNAL`; adapter exceptions are recorded as unavailable capability results.
- Forge `INVALID` and final validation `INVALID` yield `INVALID`.
- No progress or exceeding `max_steps` yields `FAILED`, not an infinite loop.
- Final rendering with missing/mismatched validation raises `ValueError`.

## Tests proving behavior

- `tests/test_workflow.py` — fast-forward, user wait, completion, and preference precedence.
- `tests/test_revisions.py` — correction history.
- `tests/test_render_service.py` — render cache key and final receipt checks.
- `tests/test_draft_projector.py`, `test_candidate_resolver.py`, and `test_signal_binding.py` — internal deterministic stages.
