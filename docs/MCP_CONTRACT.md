# Contract Forge MCP contract

Forge is stateless. ADCM owns conversation/workflow state.

## Operations

```python
async def evaluate_draft(request: ContractInput) -> ContractEvaluationResult
async def validate_final(request: ContractInput) -> FinalValidationResult
async def render_yaml(request: RenderRequest) -> RenderedContract
```

There is no stateful `submit_values(session_id, ...)` protocol.

## ContractInput
Contains:
- current nested draft snapshot;
- capability results already obtained by ADCM;
- optional `expected_schema_revision` consistency token.

It does **not** contain ConversationState, chat history, evidence history, unbound Signals or superseded candidates.

## evaluate_draft
Returns:
- `status = INCOMPLETE | COMPLETE | INVALID`;
- `CurrentSchemaView` with `schema_revision` and allowed paths;
- current requirements;
- Forge candidates (default/enrichment/derived) with provenance/priority;
- validation findings;
- capability requests.

`DEFERRED` is a finding status, not a top-level evaluate status.

## validate_final
Called by ADCM only after evaluate returns COMPLETE.

Returns:
- `VALID`
- `INVALID`
- `DEFERRED_EXTERNAL`

If external final validation is deferred, ADCM decides whether the capability can be resolved automatically. If yes, it obtains the result and retries; otherwise the ADCM outcome is `BLOCKED_EXTERNAL`.

## ADCM WorkflowOutcome mapping

```text
Forge INCOMPLETE + internal progress possible -> continue fast-forward
Forge INCOMPLETE + capability available       -> call capability, continue
Forge INCOMPLETE + user-only missing value    -> WAITING_FOR_USER
Forge COMPLETE                                -> validate_final
Final VALID                                   -> COMPLETE
Final INVALID                                 -> INVALID
Final DEFERRED_EXTERNAL + resolvable           -> capability + retry
Final DEFERRED_EXTERNAL + unavailable          -> BLOCKED_EXTERNAL
transport/application failure                  -> FAILED
```

Forge never decides `WAITING_FOR_USER`.

## Schema revision
First evaluate may use `expected_schema_revision=None`. Forge returns the revision it used. ADCM sends that revision on subsequent evaluate/validate/render calls. A revision mismatch is a schema-change condition, not something Forge silently ignores.

## Rendering
`RenderMode = DRAFT | FINAL`.

FINAL rendering requires VALID final validation for the same `draft_hash` and `schema_revision`. Rendering is a separate operation and is done after the turn fast-forward loop stabilizes, not after every evaluate call.

## Enrichment storage
Forge keeps enrichment storage behind its own port:
- `JsonEnrichmentRepository`
- future `GitHubEnrichmentRepository`
- optional `CompositeEnrichmentRepository`

ADCM does not know where enrichment rules are stored.
