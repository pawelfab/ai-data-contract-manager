# Stage 2 — Fast-forward workflow, schema-view replacement, corrections, and capabilities

## Goal

One ADCM user turn can advance through all deterministically resolvable Forge stages, capability requests, candidate binding, correction/reprojection, and final validation until the workflow is stable. `WorkflowRunner` replaces the current schema view on every stateless Forge evaluation, retries deferred capabilities when possible, and returns only the canonical ADCM outcomes. It never treats a Forge `DEFERRED` finding as a top-level status and never lets a stale branch remain in the draft.

## Why this stage exists

The current `WorkflowRunner` is the reference fast-forward loop, but it needs a contract that makes ordering, retries, correction behavior, and failure mapping explicit before a real Forge transport is added. The most dangerous regressions are accumulating `allowed_paths`, stopping after an empty-requirement candidate stage, silently accepting a schema revision change, or returning a user prompt before external dependencies have been attempted.

## Preconditions

- Stage 0 ownership/configuration is explicit and Stage 1 domain models, evidence, resolution, paths, and projection invariants pass.
- A `ContractForgePort` implementation (the current mock is sufficient for unit tests) supports stateless `evaluate_draft`, `validate_final`, and `render_yaml` contracts.
- `ConversationState` is the sole workflow state owner; Forge receives only the current draft snapshot and capability results.
- A deterministic fake `TurnInterpretation` can be supplied in workflow tests; semantic parser behavior is not a workflow precondition.

## Scope

- Define and implement `WorkflowRunner.run_until_stable` ordering and its compatibility alias `run`.
- Replace `WorkflowState.current_schema_view` on every evaluation and reproject from all non-superseded resolved values.
- Bind legal signals, expand legal preferences, ingest Forge candidates with evidence/provenance, resolve, and reevaluate whenever state or capabilities changed.
- Route `CapabilityRequest` values through the longest-prefix `CapabilityRouter`, persist `CapabilityResult`, and retry Forge deterministically.
- Supersede correction history and source candidates without deletion; ensure corrections can remove branch-specific paths from the current draft.
- Map evaluation/final-validation outcomes to `WAITING_FOR_USER`, `BLOCKED_EXTERNAL`, `COMPLETE`, `INVALID`, or `FAILED` exactly as specified.
- Surface schema revision mismatches as an explicit failure/change condition; never silently adopt a new revision.
- Keep rendering separate; this stage may return the stable artifact identity but does not render after every internal evaluation.

## Out of scope / Do not do

- Do not call external MCPs directly from Forge or from the domain layer; all capabilities go through `CapabilityRouter`.
- Do not add a background Forge retry/resume worker, event bus, graph framework, or hidden session inside Forge.
- Do not make `WorkflowRunner` parse natural language, select semantic precedence, or write `ContractDraft` directly.
- Do not union schema views, delete old candidates/signals, or use missing-path count as a substitute for Forge status.
- Do not add HTTP endpoints, durable CAS, UI, or a production Forge protocol adapter here.

## Architectural boundaries

- **ADCM application:** owns orchestration, current state, capability routing, stable outcome, and whether a dependency is user-resolvable or externally blocked.
- **Contract Forge:** evaluates the supplied snapshot and returns the current schema view, requirements, candidates, findings, and capability requests; it does not call MCPs or choose ADCM outcomes.
- **LLM:** is upstream of this stage and supplies typed interpretations only; it never mutates a draft or authorizes a path.
- **Other MCPs:** are invoked only through registered capability handlers and return capability results/evidence.
- **Airflow DAG Generator:** is not invoked by the fast-forward loop; runtime DSL is preserved.

## Invariants

- The current schema view replaces, never accumulates, prior allowed paths.
- No draft path exists without current Forge authorization.
- A user turn may call Forge repeatedly; Forge itself never resumes in the background.
- `evaluate_draft` top-level statuses are only `INCOMPLETE`, `COMPLETE`, and `INVALID`.
- `ValidationFindingStatus.DEFERRED` names a dependency; ADCM decides whether it can satisfy it.
- `validate_final` statuses are `VALID`, `INVALID`, and `DEFERRED_EXTERNAL`.
- User-visible response generation occurs only after the internal turn stabilizes (the response/API work is completed later).
- History is superseded, not deleted; candidate tie-breaking remains deterministic.

## Files affected

| File | Action | Purpose |
|---|---|---|
| `src/adcm/application/workflow_runner.py` | MODIFY | Implement the ordered fast-forward loop, revision handling, capability retry, and canonical outcome mapping. |
| `src/adcm/application/capability_router.py` | MODIFY | Preserve longest-prefix routing and explicit missing-handler behavior. |
| `src/adcm/application/chat_service.py` | MODIFY | Keep load → interpret → apply → workflow → save ordering; do not compose the final response here until Stage 6. |
| `src/adcm/application/turn_processor.py` | MODIFY if required | Ensure corrections supersede signals/candidates and preserve revision/audit history. |
| `src/adcm/domain/models.py` | MODIFY if required | Add typed dependency/error/receipt fields without changing canonical enum values. |
| `src/adcm/adapters/mcp/mock_contract_forge.py` | MODIFY | Expose deterministic branch changes, deferred findings, and revision mismatch behavior for tests. |
| `tests/test_workflow.py` | MODIFY | Cover multi-evaluation fast-forward, empty-requirement progress, deferred capabilities, final validation, and stable outcomes. |
| `tests/test_draft_projector.py` | MODIFY | Add correction branch reprojection coverage. |
| `tests/test_revisions.py` | MODIFY | Cover correction supersession through workflow candidates. |
| `docs/TURN_LIFECYCLE.md` | MODIFY | Synchronize ordering and stable-outcome semantics. |
| `docs/architecture/flows/contract-forge-workflow.md` | MODIFY | Document the loop and error mapping. |
| `docs/architecture/flows/turn-lifecycle.md` | MODIFY | Keep response-after-stabilization boundary explicit. |
| `docs/ISSUES_AND_RESOLUTIONS.md` | MODIFY | Record any resolved loop/revision discrepancy. |

## Public contracts

- `WorkflowRunner.run_until_stable(state: ConversationState) -> WorkflowOutcome` is the primary orchestration method; `run` remains a compatibility alias.
- `CapabilityRouter.register(prefix, handler)`, `can_execute(capability)`, and `execute(capability, args)` route to the longest matching prefix and raise `KeyError` when no handler exists.
- `CapabilityHandlerPort.execute(capability: str, args: dict[str, Any]) -> dict[str, Any]` remains the adapter boundary.
- `WorkflowOutcome` exposes canonical status, missing paths, draft hash/change flag, schema revision, reason, and an optional `FinalValidationReceipt`.
- `WorkflowState` stores only the current schema view/stage, current requirements/evaluation status, and obtained capability results; it does not contain chat history or superseded candidate data sent to Forge.

## Inputs and outputs

Each evaluation input is:

```python
ContractInput(
    draft=state.contract_draft.values,
    capability_results=state.workflow.capability_results,
    expected_schema_revision=current_revision_or_none,
)
```

Each evaluation output is consumed as a complete snapshot: `CurrentSchemaView`, requirements, Forge `ExternalCandidate` values, findings, and capability requests. Capability handler output becomes a typed `CapabilityResult`; it is not written into the draft until a subsequent Forge evaluation returns a candidate or requirement effect.

## State ownership

ADCM mutates `ConversationState` in memory during one turn and persists it after stabilization. Forge is stateless and sees no `ConversationState`, raw messages, Evidence history, unbound Signals, or superseded candidates. Capability adapters own only their transient call context and return serializable results.

## Data flow

```text
current state snapshot
  -> Forge.evaluate_draft(expected revision)
  -> replace CurrentSchemaView + requirements
  -> bind signals / expand preferences / ingest Forge candidates
  -> resolve candidates -> reproject nested draft
  -> execute available capabilities (or block)
  -> evaluate again when progress exists
  -> COMPLETE evaluation -> Forge.validate_final
  -> VALID / INVALID / retry deferred external / stable outcome
```

## Required behavior / how it should work

1. Capture the starting draft hash. On each iteration send the current draft and capability results with the last accepted schema revision (or `None` on the first call).
2. Replace `current_schema_view`, `current_stage`, `pending_requirements`, and `last_evaluation_status` from the response before any binding or projection.
3. On `INVALID`, return `WorkflowOutcome.INVALID` without inventing candidates.
4. Bind/expand only against the new `allowed_paths`; append Forge candidates idempotently with deterministic sequence numbers and evidence.
5. Resolve all active candidates and rebuild the draft from the current view. A branch correction (for example CSV → Parquet) removes now-illegal delimiter paths from the draft while preserving their history.
6. For each new capability request, skip an already recorded result, route supported requests, record success/unavailable/failed status, and reevaluate after any success. An unavailable required capability maps to `BLOCKED_EXTERNAL`.
7. If evaluation is `COMPLETE`, call `validate_final` with the exact draft and schema revision. Map `VALID` to `COMPLETE` with a matching receipt and `INVALID` to `INVALID`.
8. If final validation is `DEFERRED_EXTERNAL`, retry only when a registered capability can produce the dependency; otherwise return `BLOCKED_EXTERNAL`.
9. If required paths remain unresolved after all automatic progress, return `WAITING_FOR_USER` with those paths. An empty requirement list with new candidates is progress and must continue.
10. If no state/capability progress is possible or `max_steps` is exhausted, return `FAILED` with a diagnostic reason. Transport/schema-change exceptions must be visible rather than swallowed.

## Forbidden implementation shortcuts

- Unioning historical `allowed_paths` to keep old candidates legal.
- Returning `WAITING_FOR_USER` before attempting a registered capability that could satisfy the dependency.
- Treating a Forge top-level `DEFERRED` status as valid; no such status exists.
- Calling `render_yaml` on every evaluation iteration.
- Passing `ConversationState`, history, or unbound signals into `ContractInput`.
- Catching schema revision mismatch and silently replacing the expected revision.
- Stopping on an empty `requirements` list when new candidates or a capability result changed the state.

## Error semantics

- Forge `INVALID` maps to ADCM `INVALID`.
- A schema revision mismatch is a surfaced schema-change/transport error and maps to `FAILED` (or a dedicated API error later), never silent adoption.
- Missing handler, unavailable capability, or required capability failure maps to `BLOCKED_EXTERNAL` with dependency context.
- A final invalid result maps to `INVALID` with findings retained for presentation.
- No-progress and max-step conditions map to `FAILED`.
- Persistence and interpreter failures remain adapter/application errors and are handled by later turn-completion work.

## Status semantics

Use exactly:

```text
evaluate_draft: INCOMPLETE | COMPLETE | INVALID
finding:        VALID | INVALID | DEFERRED
validate_final: VALID | INVALID | DEFERRED_EXTERNAL
ADCM outcome:   WAITING_FOR_USER | BLOCKED_EXTERNAL | COMPLETE | INVALID | FAILED
```

Forge never returns `WAITING_FOR_USER` or `BLOCKED_EXTERNAL`.

## Schema revision semantics

The first evaluation may use `expected_schema_revision=None`. Every subsequent evaluate, final validate, and later render call must use the last accepted revision. If Forge reports a changed revision while the workflow is active, surface the condition and do not merge views or artifacts across revisions.

## Rendering semantics

This stage produces a stable draft hash/revision pair for later rendering. `RenderMode.DRAFT`/`FINAL`, final-validation receipt checking, and cache behavior are implemented by the render service and exercised after stabilization; no internal loop iteration renders YAML.

## Template semantics

The loop treats template strings as values. Enrichment-time `{source}` substitution belongs to Forge; runtime `{{env}}`, `{{date:%Y%m%d}}`, and `{{var.name}}` remain unchanged for the Airflow DAG Generator.

## Arrays and paths

Every candidate path is a concrete instance path or a Forge-authorized schema path according to the domain contract. Reprojection uses `ContractPath` and wildcard authorization; branch replacement must also remove illegal array/object branches from the nested draft.

## Value precedence

ADCM resolves origin precedence and same-origin corrections. Forge candidate priority/specificity is carried on each candidate and is not recomputed from scope in `WorkflowRunner`. LLM semantics and capability payload order cannot choose a winner.

## Tests

- **Unit:** longest-prefix capability routing; duplicate candidate suppression; missing-handler mapping; no-progress/max-step errors.
- **Workflow integration:** one user turn crosses multiple evaluations, including an empty-requirement candidate stage and a newly activated requirement; deferred capability success triggers a retry; unavailable final capability maps to `BLOCKED_EXTERNAL`.
- **Correction regression:** changing a discriminator removes no-longer-legal paths while preserving historical signals/candidates.
- **Revision negative:** a changed schema revision is surfaced and does not silently adopt the new view.
- **Status contract:** no `DEFERRED` top-level evaluation and no Forge-owned `WAITING_FOR_USER`/`BLOCKED_EXTERNAL` values.

## Acceptance criteria

- The deterministic fake workflow reaches the next stage whenever candidates/capability results changed state, even when the current evaluation has no requirements.
- A supported capability is invoked at most once per request ID and its result causes reevaluation.
- A missing required capability returns `BLOCKED_EXTERNAL`; a missing user value returns `WAITING_FOR_USER`.
- COMPLETE evaluation always precedes final validation, and a VALID final receipt matches the resulting draft hash and schema revision.
- Corrections replace the current schema view and never delete history.
- All workflow tests use typed fake interpretations, not the demo NLP parser.

## Explicit non-goals

Real Forge transport/provider conformance, Pydantic AI production semantics, durable CAS/idempotent audit, HTTP/API response models, UI, and release gates remain later stages.

## Documentation updates

Update `docs/TURN_LIFECYCLE.md`, `docs/MCP_CONTRACT.md`, `docs/architecture/flows/contract-forge-workflow.md`, `docs/architecture/flows/turn-lifecycle.md`, and relevant symbol/module catalogs. Record any change to revision/error mapping in `docs/DESIGN_DECISIONS.md`.

## Completion checklist

- [ ] Fast-forward ordering and canonical outcomes are implemented and tested.
- [ ] CurrentSchemaView replacement and correction reprojection are verified.
- [ ] Capability retries and blocked mappings are deterministic.
- [ ] Schema revision mismatch is surfaced.
- [ ] No user-visible response or YAML rendering occurs before stabilization.
- [ ] No production Forge or HTTP code was introduced.

