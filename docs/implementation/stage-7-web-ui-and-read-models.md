# Stage 7 — Read-only Web UI, draft/YAML read models, and artifact reuse

## Goal

Users can inspect a session's current workflow status, nested ADCM draft preview, and Forge-rendered YAML through read-only endpoints and a minimal web UI. Read models are derived from persisted structured state and stable render receipts; they never become a second state model. YAML is read-only in the first implementation, and artifact rendering is reused by `(draft_hash, schema_revision, render_mode)` rather than rerun for unchanged content.

## Why this stage exists

Stage 6 exposes a write endpoint and stable turn receipts but deliberately keeps presentation minimal. The repository has no UI/read-model layer yet. A separate stage prevents presentation concerns from leaking into the domain/workflow and makes the final YAML safety rules visible: previews can show ADCM draft data, while canonical YAML remains Forge-owned and cannot be edited to bypass candidates/revisions.

## Preconditions

- Stage 6 HTTP turn endpoint, durable session receipt, and idempotency behavior are complete.
- Stage 3 Forge render operation and Stage 6 post-stabilization render/cache contract are available (mock rendering is sufficient for local UI tests).
- Session reads can obtain a consistent versioned snapshot and stable final-validation receipt.
- The owner has selected a minimal web/static serving approach; no framework dependency is assumed in `src/adcm/domain` or `src/adcm/application`.

## Scope

- Define typed read models for session summary, workflow status, nested draft preview, validation findings/dependencies, capability blockers, and rendered artifacts.
- Add read-only HTTP routes for current session/draft/artifact views and a minimal UI that consumes them.
- Reuse the application render service/cache for DRAFT and FINAL artifacts; call Forge only after stabilization and only when the cache key changes.
- Clearly label YAML as Forge-rendered, read-only, and tied to a draft hash/schema revision; show ADCM draft preview separately.
- Add safe redaction/pagination limits for messages/evidence and a deterministic representation of missing user paths/external blockers.

## Out of scope / Do not do

- Do not add POST/PATCH endpoints that mutate contracts, signals, candidates, or YAML.
- Do not parse or accept edited YAML as a direct state update.
- Do not implement a second renderer, schema validator, or frontend-specific workflow engine.
- Do not expose hidden model reasoning, raw credentials, or unrestricted Evidence content.
- Do not add live capability calls from the UI; refresh reads only persisted/stable state.

## Architectural boundaries

- **ADCM read-model layer:** projects persisted state and stable receipts into immutable presentation models.
- **Contract Forge:** remains the only canonical YAML renderer and validator.
- **LLM:** is not called by read endpoints; prior assistant text is displayed as a receipt, not regenerated on refresh.
- **Other MCPs:** are not called by UI/read routes.
- **Airflow DAG Generator:** consumes runtime DSL later; the UI displays it unchanged.

## Invariants

- Read models are derived views; `ConversationState` remains authoritative.
- YAML is read-only and only shown for the matching draft hash/schema revision/render mode.
- FINAL artifact requires VALID final validation for the same hash/revision.
- Render happens after stabilization, never after every Forge iteration.
- Draft projection already enforces current schema authorization; UI cannot resurrect illegal historical paths.
- Runtime Contract DSL remains verbatim.

## Files affected

| File | Action | Purpose |
|---|---|---|
| `src/adcm/api/read_models.py` | NEW | Define immutable Pydantic read models for session/draft/validation/artifact views. |
| `src/adcm/api/read_only.py` | NEW | Implement GET-only routes and authorization-neutral read projection. |
| `src/adcm/application/render_service.py` | MODIFY | Expose cache hit/miss/artifact metadata needed by read models without moving rendering authority. |
| `src/adcm/application/context_builder.py` | MODIFY if bounded read data is shared | Keep semantic context and presentation projections separate. |
| `src/adcm/domain/models.py` | MODIFY only for stable receipt fields | Preserve nested draft/hash/revision data used by read models. |
| `web/` | NEW | Minimal static/server-rendered read-only UI assets chosen by the repository owner. |
| `tests/test_read_models.py` | NEW | Projection, redaction, nested arrays, status, and cache metadata tests. |
| `tests/test_api_read_only.py` | NEW | GET routes, missing session/artifact, and no-mutation behavior. |
| `tests/test_render_service.py` | MODIFY | Cache key, FINAL precondition, and post-stabilization call count. |
| `docs/ARCHITECTURE.md` | MODIFY | Document presentation/read-model boundary. |
| `docs/TURN_LIFECYCLE.md` | MODIFY | Document read-after-stabilization/render ordering. |
| `docs/ADAPTERS_AND_DEPLOYMENT.md` | MODIFY | Document web/read-only deployment assumptions. |
| `docs/DESIGN_DECISIONS.md` | MODIFY | Record YAML read-only decision and artifact key. |

## Public contracts

Read models are immutable Pydantic DTOs. At minimum:

```python
class SessionReadModel(BaseModel):
    session_id: UUID
    storage_version: int
    workflow_status: WorkflowOutcomeStatus | None
    current_stage: str | None
    schema_revision: str | None
    draft_hash: str | None
    missing_paths: list[str]
    external_block_reason: str | None
    draft: dict[str, Any]

class ArtifactReadModel(BaseModel):
    draft_hash: str
    schema_revision: str
    mode: RenderMode
    content: str
    read_only: bool = True
```

Routes are GET-only and may be exposed as:

```text
GET /sessions/{session_id}
GET /sessions/{session_id}/draft
GET /sessions/{session_id}/artifacts/{mode}
```

The exact framework route registration is private; the models and read-only semantics are not.

## Inputs and outputs

Inputs are a consistent session snapshot, optional stored `FinalValidationReceipt`, and an artifact cache lookup. Outputs are nested JSON-shaped draft/status models and Forge-rendered YAML content with hash/revision/mode metadata. Absent sessions/artifacts return typed 404 read errors; stale cache entries are not served as current.

## State ownership

Read routes do not own mutable state. `SessionRepositoryPort` owns loading the snapshot; `ContractRenderService`/Forge owns artifact content; the UI owns only transient display state in the browser. No read model is written back as `ConversationState`.

## Data flow

```text
GET request
  -> load consistent VersionedSession
  -> project Session/Draft read model
  -> artifact key lookup
       -> cache hit: return artifact
       -> miss and stable receipt: Forge.render_yaml once, cache, return
  -> read-only HTTP/UI response
```

## Required behavior / how it should work

1. Load a consistent snapshot and expose current stage/status/schema revision/draft hash without recomputing workflow.
2. Project the nested `ContractDraft.values` as a read-only JSON structure; preserve array indices and omit no-longer-authorized values already removed by projection.
3. Show pending required paths, deferred dependencies, and safe reasons for `WAITING_FOR_USER`/`BLOCKED_EXTERNAL` without exposing internal provider traces.
4. For DRAFT artifact requests, serve a cache hit or call Forge render once for the exact key after stabilization. For FINAL, require a matching VALID receipt and reject otherwise.
5. Label YAML as Forge-rendered and read-only. Any future editing feature must parse/validate edits into normal user candidates/revisions and is explicitly not part of this stage.
6. Bound message/evidence excerpts and redact secrets/credentials. Refreshing a page must not invoke the LLM or external capabilities.
7. Serve the minimal UI through the selected web adapter; the UI must use read routes and the Stage 6 message endpoint only for new user turns, never direct domain imports.

## Forbidden implementation shortcuts

- Rendering YAML from the UI or using a Python YAML dump as a replacement for Forge.
- Returning a stale artifact after schema revision or draft hash changes.
- Exposing a mutable reference to `ConversationState.contract_draft.values`.
- Calling WorkflowRunner, LLM, or capabilities on GET.
- Providing an “edit YAML” form that writes directly to the draft.
- Accumulating historical allowed paths in the read model.

## Error semantics

- Missing session: typed 404.
- Missing artifact or FINAL without matching VALID receipt: typed 404/409 according to route contract; never render an invalid final artifact.
- Schema revision mismatch during render: typed 409/change error; do not serve prior-revision content as current.
- Forge/render unavailable: typed 503/read error; existing cached content may be served only when its key exactly matches the requested stable identity and policy allows stale reads (default: no stale content).
- Redaction/projection failure: safe 5xx without leaking raw state.

## Status semantics

Read models serialize the canonical ADCM workflow status values and do not introduce UI-specific replacements. Validation findings preserve `VALID`, `INVALID`, and `DEFERRED` plus dependency details; final validation preserves `VALID`, `INVALID`, `DEFERRED_EXTERNAL`.

## Schema revision semantics

Every artifact/read model carries the Forge schema revision. Cache lookup key is exactly `(draft_hash, schema_revision, render_mode)`; `schema_revision` is never folded into `draft_hash`. A changed revision invalidates an earlier artifact for the current view.

## Rendering semantics

`RenderMode.DRAFT` and `RenderMode.FINAL` are the only modes. FINAL requires a VALID receipt with matching hash/revision. Rendering is a post-stabilization capability and is performed at most once per new cache key; evaluation responses do not contain YAML by default.

## Template semantics

Display runtime DSL strings exactly as Forge returned them. The UI does not resolve `{source}`, `{{env}}`, `{{date:%Y%m%d}}`, or `{{var.name}}`.

## Arrays and paths

Read models preserve nested lists/objects and concrete indices. Any optional path metadata shown to the user must distinguish schema wildcard patterns from instance paths and must not be interpreted as an authorization grant.

## Value precedence

Read models show resolved values and, where appropriate, selected candidate provenance as read-only explanation. They do not recompute precedence or expose candidate controls that could bypass ADCM resolution.

## Tests

- **Read-model unit:** nested drafts/arrays, statuses, hashes/revisions, redaction, and missing-path rendering.
- **Artifact contract:** cache hit/miss, exact key components, FINAL receipt matching, schema revision mismatch, and one render after stabilization.
- **HTTP negative:** all UI/read routes are GET-only; no mutation occurs; absent/stale artifacts are explicit errors.
- **Integration:** refresh/repeated GET does not call LLM/Forge capabilities; UI new-turn action uses Stage 6 idempotency.
- **Template/privacy:** runtime DSL survives round trip and secrets/hidden reasoning are absent.

## Acceptance criteria

- Read-only routes and a minimal UI display current nested draft, canonical status, and appropriately keyed YAML artifacts.
- No GET call mutates session state or invokes semantic/capability workflows.
- FINAL artifact cannot be served without same-hash/same-revision VALID receipt.
- Cache key behavior is observable and tested; unchanged artifacts are not rerendered.
- YAML edits are impossible in the first implementation.

## Explicit non-goals

Editable contract/YAML, authentication policy, real-contract end-to-end gates, and deployment manifests are deferred. The UI is not a second onboarding workflow.

## Documentation updates

Update `docs/ARCHITECTURE.md`, `docs/TURN_LIFECYCLE.md`, `docs/ADAPTERS_AND_DEPLOYMENT.md`, architecture module/symbol docs, `docs/DESIGN_DECISIONS.md`, and API documentation if routes are named differently.

## Completion checklist

- [ ] Read models are immutable projections of persisted state.
- [ ] GET routes/UI are read-only and bounded/redacted.
- [ ] Forge remains the sole YAML renderer.
- [ ] Hash/revision/mode cache semantics and FINAL gating pass.
- [ ] Runtime DSL is preserved; no editor or direct mutation path exists.

