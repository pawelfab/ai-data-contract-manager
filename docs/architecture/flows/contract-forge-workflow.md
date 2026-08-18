---
flow: contract-forge-fast-forward
entry_points:
  - src/adcm/application/workflow_runner.py::WorkflowRunner.run_until_stable
  - src/adcm/application/render_service.py::ContractRenderService.render
last_verified: working-tree-2026-08-18
---

# Contract Forge workflow

## Preconditions

`WorkflowRunner` has a `ContractForgePort`; capability routing is optional. The current nested `ContractDraft` and any prior capability results live in ADCM state.

## Evaluation loop

1. Send `ContractInput(draft, capability_results, expected_schema_revision)` to `evaluate_draft`.
2. Replace `WorkflowState.current_schema_view`; never union prior allowed paths.
3. On Forge `INVALID`, return ADCM `INVALID`.
4. Bind signals and expand preferences only against current allowed paths; ingest Forge candidates with provenance.
5. Resolve candidates deterministically and rebuild the nested draft through `DraftProjector.project`.
6. Execute supported capability requests through `CapabilityRouter`; store `CapabilityResult` and reevaluate. Return `BLOCKED_EXTERNAL` if required capability resolution is unavailable.
7. Return `WAITING_FOR_USER` when required paths remain unresolved.
8. On Forge `COMPLETE`, call `validate_final`. Map VALID to `COMPLETE`, INVALID to `INVALID`, and unresolved DEFERRED_EXTERNAL to `BLOCKED_EXTERNAL`.
9. Return `FAILED` on no progress or `max_steps` exhaustion.

## Rendering

`ContractRenderService.render` is separate from evaluation. DRAFT may render directly. FINAL requires a VALID `FinalValidationReceipt` whose draft hash and schema revision match. Results are cached by `RenderCacheKey(draft_hash, schema_revision, mode)`.

## Error and compatibility behavior

Capability adapter exceptions are recorded as unavailable capability results. Schema revision mismatch handling belongs to Forge; the mock adapter raises on mismatch. `WorkflowRunner.run` remains a compatibility alias for `run_until_stable`.

## Tests

`tests/test_workflow.py`, `tests/test_draft_projector.py`, `tests/test_candidate_resolver.py`, and `tests/test_render_service.py`.

