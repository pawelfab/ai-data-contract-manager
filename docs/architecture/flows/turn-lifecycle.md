---
flow: user-turn-lifecycle
entry_points:
  - src/adcm/application/chat_service.py::ChatService.handle_user_message
last_verified: working-tree-2026-08-19
---

# User turn lifecycle

## Trigger and outcome

A caller submits `(session_id, text)`. The result is the persisted `ConversationState` and a stable `WorkflowOutcome`.

## Execution

1. `ChatService.handle_user_message` loads state or creates `ConversationState`.
2. `AgentContextBuilder.build` projects compact active state and recent messages.
3. `SemanticInterpreterPort.interpret_turn` returns `TurnInterpretation`.
4. `TurnProcessor.apply_user_turn` appends message evidence, signals/preferences/corrections, and revisions; it does not edit the draft.
5. `WorkflowRunner.run_until_stable` evaluates the draft against stateless Forge, replaces the schema view, binds/expands candidates, resolves, reprojects, and resolves capabilities until stable.
6. `SessionRepositoryPort.save` persists the state.
7. The caller receives an outcome: `WAITING_FOR_USER`, `BLOCKED_EXTERNAL`, `COMPLETE`, `INVALID`, or `FAILED`.

## Side effects and transactions

State mutation occurs in memory before a single repository save. There is no database transaction abstraction. A persistence adapter failure propagates from `load` or `save`. Forge/capability calls occur before save and may have external side effects depending on adapters.

## Idempotency and concurrency

Candidate keys suppress exact semantic duplicates inside a state. Binders skip wildcard schema patterns and reset signals to `unbound` when a replacement view no longer offers exactly one concrete match. Resolution preflights the complete candidate set, computes every winner, builds every resolution, and only then commits statuses. Duplicate IDs, non-finite confidence, or a policy-rank tie therefore leave all input statuses unchanged. The session repository protocol exposes no compare-and-swap or locking, so concurrent writes to one session are not coordinated by the application layer.

## Tests

`tests/test_workflow.py`, `tests/test_revisions.py`, `tests/test_signal_binding.py`, and `tests/test_rule_based_interpreter.py` prove the deterministic stages used by the turn.
