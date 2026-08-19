# Stage 6 — Turn completion, HTTP API, idempotency, and post-stabilization response

## Goal

ADCM exposes a small HTTP boundary for user turns. A request is interpreted, applied, fast-forwarded, persisted with optimistic versioning, audited, optionally rendered after stabilization, and answered with a stable typed response. A client retry carrying the same idempotency key returns the original receipt without re-running semantic interpretation, Forge, capabilities, or rendering. The API never exposes a partially stabilized turn as if it were complete.

## Why this stage exists

`src/adcm/api` is currently empty and `ChatService.handle_user_message` returns raw state plus `WorkflowOutcome` without a response composer or idempotency policy. Stages 1–5 provide domain/workflow, semantic, Forge, persistence, and audit boundaries; this stage composes them into one externally observable turn contract while keeping rendering and UI read models separate.

## Preconditions

- Stage 2 fast-forward and Stage 3 provider contract (or the test mock) are stable.
- Stage 4 provides `ResponseComposerPort` and semantic adapter behavior.
- Stage 5 provides versioned session persistence and idempotent audit append.
- A supported HTTP/ASGI runtime is selected by the repository owner; no new framework is assumed by domain code.

## Scope

- Define typed HTTP request/response models for posting a user message and returning a stable outcome/assistant response.
- Extend `ChatService` or add a turn-completion application service that enforces load → idempotency check → interpret → apply → fast-forward → persist → audit → post-stabilization render (when requested) → compose response ordering.
- Add an idempotency-key record/receipt owned by the session state or a repository-backed idempotency store, with same-key/same-payload replay and same-key/different-payload conflict.
- Add an HTTP adapter with a single message endpoint and deterministic mapping of validation, conflict, external-block, and application failures.
- Ensure final validation/render receipts are tied to the exact draft hash and schema revision.
- Keep user-visible draft preview/YAML presentation read-only; richer read models and UI belong to Stage 7.

## Out of scope / Do not do

- Do not add a second workflow runner, state store, or Forge protocol.
- Do not let HTTP handlers mutate `ContractDraft`, candidates, or revisions directly; call the application service.
- Do not re-run a completed turn on idempotent retry, even if the response composer previously failed.
- Do not render on every evaluation, expose editable YAML, or parse client-supplied YAML into state.
- Do not add authentication/authorization policy, deployment manifests, or a large web framework abstraction beyond the selected adapter.

## Architectural boundaries

- **ADCM application/API:** owns request validation, idempotency, turn sequencing, stable outcome mapping, and response composition invocation.
- **Forge:** remains stateless and authoritative for evaluation, final validation, schema revision, and YAML.
- **LLM:** interprets/composes semantics only; it never writes state or chooses an HTTP outcome.
- **Other MCPs:** are capability handlers called by WorkflowRunner; HTTP never calls them directly.
- **Airflow DAG Generator:** is not called by the API; runtime DSL in rendered output remains opaque.

## Invariants

- User-visible response is produced only after internal state is stable and persistence/audit ordering has been applied.
- Same idempotency key and same request payload return the original receipt without duplicate side effects.
- Same idempotency key with a different payload is rejected.
- `WAITING_FOR_USER`, `BLOCKED_EXTERNAL`, `COMPLETE`, `INVALID`, and `FAILED` are the only ADCM workflow statuses.
- LLM/external MCP output never mutates the draft directly.
- Schema revision mismatch and persistence conflict are surfaced, not silently retried with changed state.
- YAML is rendered separately after stabilization and never treated as editable state.

## Files affected

| File | Action | Purpose |
|---|---|---|
| `src/adcm/api/models.py` | NEW | Define `UserMessageRequest`, idempotency metadata, and typed `TurnHttpResponse`/error models. |
| `src/adcm/api/http.py` | NEW | Implement the selected HTTP/ASGI adapter and endpoint routing. |
| `src/adcm/application/chat_service.py` | MODIFY | Orchestrate idempotency-aware turn completion and return a stable response object. |
| `src/adcm/application/response_composer.py` | MODIFY | Invoke the Stage 4 composer only after stable persistence/render decisions. |
| `src/adcm/application/render_service.py` | MODIFY | Integrate post-stabilization DRAFT artifact reuse without per-evaluation rendering. |
| `src/adcm/domain/models.py` | MODIFY | Add typed turn receipt/idempotency records while preserving workflow enums. |
| `src/adcm/ports/session_repository.py` | MODIFY if needed | Support atomic idempotency receipt persistence with the versioned session. |
| `tests/test_chat_service.py` | NEW | Turn sequencing, response composition, and persistence/audit behavior. |
| `tests/test_api.py` | NEW | Endpoint request/response/error/idempotency contract. |
| `tests/test_render_service.py` | MODIFY | Verify one render after stabilization and cache reuse from turn completion. |
| `docs/TURN_LIFECYCLE.md` | MODIFY | Document the external turn contract and ordering. |
| `docs/MCP_CONTRACT.md` | MODIFY if response/render boundary changes | Keep stateless Forge invocation rules current. |
| `docs/ADAPTERS_AND_DEPLOYMENT.md` | MODIFY | Document HTTP composition and adapter selection. |
| `docs/DESIGN_DECISIONS.md` | MODIFY | Record idempotency and conflict policy. |

## Public contracts

The transport-neutral request/response models are:

```python
class UserMessageRequest(BaseModel):
    text: str
    idempotency_key: str

class TurnHttpResponse(BaseModel):
    session_id: UUID
    idempotency_key: str
    outcome: WorkflowOutcome
    assistant_text: str
    draft_preview: dict[str, Any]
    rendered_artifact_available: bool = False
```

Endpoint:

```text
POST /sessions/{session_id}/messages
```

The request body must contain a non-empty message and idempotency key. The response is the persisted receipt for that key. Framework-specific handler signatures and middleware remain private to `src/adcm/api/http.py`.

## Inputs and outputs

Input: session UUID, `UserMessageRequest`, optional transport metadata needed for tracing (not domain state). Output: `TurnHttpResponse` containing the stable `WorkflowOutcome`, safe nested draft preview, assistant text, and artifact availability; it must not expose raw Evidence, hidden model reasoning, provider credentials, or mutable repository objects.

HTTP error mapping:

| Condition | Status | Contract |
|---|---:|---|
| malformed request/session ID | 400 | typed validation error |
| same idempotency key/different payload | 409 | idempotency conflict |
| storage version conflict | 409 | concurrency conflict; no replay |
| schema revision change | 409 or 503 by adapter policy | explicit schema-change error |
| unavailable required capability | 200 with `BLOCKED_EXTERNAL` outcome | stable workflow result |
| semantic/Forge/persistence failure | 5xx | safe retry guidance, no fabricated success |

## State ownership

The application service owns turn sequencing and the idempotency receipt; the versioned session repository atomically persists both with `ConversationState`. The HTTP adapter holds no session state between requests. Response text is a read-only artifact of a stable receipt.

## Data flow

```text
POST session/message + idempotency key
  -> load VersionedSession
  -> replay stored receipt or validate new payload
  -> interpret -> apply Evidence/signals/preferences
  -> WorkflowRunner fast-forward/stabilize
  -> save state + receipt (version check)
  -> append idempotent audit
  -> render once if artifact key changed/needed
  -> compose assistant response
  -> HTTP TurnHttpResponse
```

## Required behavior / how it should work

1. Validate the session ID, non-empty text, and idempotency key before invoking an interpreter or Forge.
2. Load the versioned session. If the key exists with the same request fingerprint, return its stored response. If the key exists with a different fingerprint, return a conflict.
3. Invoke the semantic interpreter once, apply the turn through `TurnProcessor`, and run the complete Stage 2 fast-forward loop.
4. Persist the resulting state and idempotency receipt using the expected storage version. On a conflict, return a 409 and do not re-run the turn automatically.
5. Append audit events with stable IDs. Audit failure after a successful state save is explicit/retryable and does not create a second turn.
6. After stabilization, call `ContractRenderService` at most once for a changed `(draft_hash, schema_revision, render_mode)` key when the requested response needs an artifact. Never attach YAML to every Forge evaluation.
7. Invoke `ResponseComposerPort` only after the state/receipt is stable and provide a redacted `ResponseContext`.
8. Store the final response receipt so retries return the same assistant text/outcome/draft hash, even if the model provider is unavailable later.

## Forbidden implementation shortcuts

- Using the client idempotency key only in process memory.
- Hashing raw text with a new random salt on every request or ignoring session ID in the fingerprint.
- Calling the interpreter/Forge before checking an existing idempotency receipt.
- Returning a 200 “success” with an unstable/unsaved state.
- Treating a `BLOCKED_EXTERNAL` outcome as an HTTP transport failure or a user-only missing field.
- Allowing the client to submit YAML that bypasses candidates/revisions.

## Error semantics

- Request validation: deterministic 400 response.
- Idempotency conflict or storage concurrency conflict: 409; no side effect beyond safe audit of the conflict if configured.
- `WAITING_FOR_USER`, `BLOCKED_EXTERNAL`, `INVALID`, `FAILED` are stable workflow results, not necessarily HTTP errors; body carries the canonical outcome and assistant text.
- Interpreter/Forge transport failure before save: 5xx and no committed receipt.
- Persistence conflict after external calls: 409; caller may retry with a new turn/key after inspecting current state.
- Composer/render failure after state save: return a safe 5xx or stored fallback text while preserving the committed receipt; never rerun the turn implicitly.

## Status semantics

The response must serialize only the canonical `WorkflowOutcomeStatus` values. Forge statuses remain nested in diagnostics/receipts only and are never renamed. A user-facing message may explain `WAITING_FOR_USER` or `BLOCKED_EXTERNAL`, but cannot change the enum.

## Schema revision semantics

The response includes the stable workflow's schema revision and draft hash when available. `render_yaml` and final validation use the exact revision from the stable receipt; a mismatch is surfaced as a conflict/change error and is never silently adopted.

## Rendering semantics

Rendering occurs after stabilization and persistence decision. `DRAFT` may be rendered for preview; `FINAL` requires a VALID final-validation receipt for the same draft hash and schema revision. Artifact cache key is `(draft_hash, schema_revision, render_mode)` and is not part of request idempotency fingerprint except through the stored receipt.

## Template semantics

The API and response composer display runtime Contract DSL verbatim. They do not resolve `{source}` or translate `{{...}}`; Forge and the later DAG Generator retain their respective ownership.

## Arrays and paths

`draft_preview` is nested JSON/YAML-shaped data. API clients receive concrete array indices, not path/value maps or schema wildcard permissions. Incoming text describing arrays remains semantic input and is bound only through Forge-authorized candidates.

## Value precedence

The API does not resolve values. Candidate precedence and correction sequencing occur in Stages 1–2; the response only reports the stable result and safe explanation.

## Tests

- **Application unit:** idempotency fingerprint/replay, same-key conflict, stable response storage, composer ordering, and render-call count.
- **HTTP contract:** 400 validation, 409 conflicts, canonical outcome serialization, safe 5xx errors, and nested draft preview.
- **Integration:** one request persists state/audit/receipt; retry causes no interpreter, Forge, capability, render, or audit duplication.
- **Negative:** response cannot be generated before stabilization; YAML cannot be submitted as a direct mutation.
- **Revision:** schema revision mismatch maps to explicit conflict/change response and does not corrupt cache/receipt.

## Acceptance criteria

- `POST /sessions/{session_id}/messages` is documented and returns a typed stable receipt.
- Repeating an identical request with the same key returns byte-equivalent semantic response data and no duplicate side effects.
- Same key/different text returns 409; stale storage version returns 409 without overwrite.
- Response composition happens after save/audit/stabilization, and render is called at most once per changed artifact key.
- All five ADCM workflow statuses serialize consistently.

## Explicit non-goals

Read-only UI/read-model endpoints, editable YAML, authentication/authorization, deployment manifests, and end-to-end real-contract gates are Stages 7–8.

## Documentation updates

Update `docs/TURN_LIFECYCLE.md`, `docs/ADAPTERS_AND_DEPLOYMENT.md`, API/port symbol catalogs, `docs/DESIGN_DECISIONS.md`, and the master plan status/link if the endpoint contract changes.

## Completion checklist

- [ ] Typed request/response and endpoint contract are implemented.
- [ ] Idempotency is durable and conflict-aware.
- [ ] Turn ordering reaches a stable outcome before response generation.
- [ ] Persistence/audit/render call counts and failure paths are tested.
- [ ] Canonical statuses, hashes, and schema revisions are preserved.

