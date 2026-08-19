# Stage 5 — Durable versioned sessions and idempotent audit delivery

## Goal

ADCM can persist a session durably with optimistic version checks and deliver audit events idempotently. A concurrent or retried write cannot overwrite a newer session silently, and replaying the same audit event ID does not duplicate it. Business revision history remains distinct from the storage version. The reference memory/JSON adapters continue to work for tests/local runs, while production adapters can be added behind the same ports without changing domain ownership.

## Why this stage exists

The current `SessionRepositoryPort` saves a `ConversationState` without a compare-and-swap token, and `JsonFileSessionRepository` writes directly with no atomic/version check. `AuditSinkPort.append` has no explicit duplicate semantics. HTTP retries and multi-instance deployments would therefore lose turns or duplicate audit records. This stage establishes durable boundaries before API idempotency is exposed.

## Preconditions

- Stages 1–4 provide stable domain, workflow, semantic, and response contracts.
- `ConversationState.revision` and `Revision` remain business history; they are not silently repurposed as a storage sequence.
- No database-migration root or deployment manifest exists; adding one is out of scope and requires a separate repository decision.
- The selected durable backend and filesystem/cloud permissions are available for integration tests.

## Scope

- Add a storage-version/optimistic-concurrency contract separate from business revisions.
- Evolve `SessionRepositoryPort` so load returns the current version and save requires an expected version (or an explicit create-if-absent token), with a typed conflict error.
- Update `InMemorySessionRepository` and `JsonFileSessionRepository` for deep-copy/versioned behavior; use recoverable atomic writes for JSON files where practical.
- Define idempotent `AuditSinkPort.append`: event ID is the idempotency key, repeated delivery is a no-op, and payloads for the same ID must not diverge silently.
- Update `JsonlAuditSink` and test doubles to implement duplicate detection without claiming to persist hidden model reasoning.
- Ensure load/save/audit failure ordering and retry behavior are explicit for the turn service.

## Out of scope / Do not do

- Do not introduce a database schema, migration directory, Event Sourcing, CQRS framework, Kafka, or distributed transaction coordinator.
- Do not delete or rewrite historical `Revision`, `Signal`, `ValueCandidate`, or `AuditEvent` records during correction.
- Do not use a UUID as a storage version or candidate tie-breaker.
- Do not make the audit sink the authoritative session store or derive workflow state from audit replay.
- Do not expose provider prompts, hidden reasoning, secrets, or raw model traces in audit payloads.

## Architectural boundaries

- **ADCM:** owns `ConversationState`, business revisions, candidate/history semantics, and when a state/audit write is attempted.
- **Session adapter:** owns durable serialization, storage version, atomicity, and backend-specific conflict detection.
- **Audit adapter:** owns append-only delivery and event-ID idempotency; it is not a source of domain truth.
- **Forge/LLM/MCP:** remain stateless/provider boundaries; their calls occur before persistence and are represented only by safe typed outcomes/evidence.
- **DAG Generator:** has no persistence role.

## Invariants

- History is superseded/rejected, never deleted to resolve a conflict.
- Storage version and business revision are distinct values.
- A session write with a stale expected version fails explicitly and cannot overwrite newer state.
- Replaying an identical `AuditEvent.id` is idempotent; reusing the ID with a different payload is an error.
- Audit records capture explicit domain decisions and redacted boundary payloads, never chain-of-thought.
- `ConversationState` remains the authoritative application state; conversation history is not used as state.

## Files affected

| File | Action | Purpose |
|---|---|---|
| `src/adcm/domain/models.py` | MODIFY | Add a typed storage-version/session-record contract if needed; keep business `revision` semantics intact. |
| `src/adcm/ports/session_repository.py` | MODIFY | Define versioned load/save and a typed concurrency-conflict boundary. |
| `src/adcm/ports/audit_sink.py` | MODIFY | Define event-ID idempotency and duplicate-payload conflict behavior. |
| `src/adcm/adapters/persistence/memory.py` | MODIFY | Implement version checks and deep-copy semantics for tests. |
| `src/adcm/adapters/persistence/json_file.py` | MODIFY | Implement versioned, recoverable JSON persistence without cross-process lock claims. |
| `src/adcm/adapters/logging/jsonl_audit.py` | MODIFY | Implement append-once by event ID and safe serialization. |
| `src/adcm/application/chat_service.py` | MODIFY | Use versioned save/retry/conflict behavior without rerunning a turn blindly. |
| `tests/test_persistence_versioning.py` | NEW | Round-trip, stale-write, create, and adapter failure tests. |
| `tests/test_audit_idempotency.py` | NEW | Duplicate and same-ID/different-payload tests. |
| `tests/test_revisions.py` | MODIFY | Distinguish business revision history from storage version. |
| `docs/ADAPTERS_AND_DEPLOYMENT.md` | MODIFY | Document durable backend expectations and local limitations. |
| `docs/TURN_LIFECYCLE.md` | MODIFY | Document persistence/audit ordering and conflict outcomes. |
| `docs/DESIGN_DECISIONS.md` | MODIFY | Record version-token and audit-ID decisions. |

## Public contracts

Use a single explicit versioned repository contract. The concrete names may follow project conventions, but the semantics are fixed:

```python
class VersionedSession(BaseModel):
    state: ConversationState
    storage_version: int

class SessionRepositoryPort(Protocol):
    async def load(self, session_id: UUID) -> VersionedSession | None: ...
    async def save(
        self,
        state: ConversationState,
        *,
        expected_storage_version: int | None,
    ) -> VersionedSession: ...
```

`expected_storage_version=None` is allowed only for create-if-absent; an existing session must produce a conflict. A stale expected version raises a typed `SessionConcurrencyError` containing session ID and current version, without exposing secrets.

`AuditSinkPort.append(event: AuditEvent) -> None` is idempotent by `event.id`. The first payload is retained; a duplicate identical payload is a no-op; a duplicate ID with different immutable fields raises a typed audit conflict.

## Inputs and outputs

Session adapters accept a complete `ConversationState` snapshot and expected storage token; they return a new storage token or explicit conflict/failure. Audit adapters accept a fully formed, redacted `AuditEvent`. No adapter accepts a patch that can bypass domain validation.

## State ownership

ADCM owns all business state and decides the event payload. The storage adapter owns only serialization/version metadata. The audit sink owns delivery bookkeeping; it does not reconstruct `ConversationState` or select winners.

## Data flow

```text
load(session_id)
  -> VersionedSession(state, storage_version)
  -> interpret + apply + stabilize in ADCM
  -> save(state, expected_storage_version)
  -> new storage version
  -> append redacted AuditEvent(id)
  -> duplicate retries become no-ops
```

## Required behavior / how it should work

1. Load a deep copy/immutable snapshot so caller mutation cannot bypass a repository write.
2. Save only when the expected storage version still matches; atomically publish the new snapshot and increment the storage version.
3. On a conflict, do not automatically replay the semantic turn or merge candidate histories. Return a typed conflict for Stage 6/API policy to resolve.
4. JSON-file persistence writes a temporary sibling and atomically replaces the target where supported; malformed/truncated files fail loudly and are not overwritten with an empty session.
5. Audit event IDs are generated once per domain event before retries. Re-delivery of the same event is safe; a different payload with the same ID is a data-integrity error.
6. Persist explicit value changes, candidate selection, validation outcome, and redacted boundary metadata only. Do not persist hidden model reasoning.
7. Keep in-memory adapter semantics equivalent to durable adapter semantics for version and duplicate tests.

## Forbidden implementation shortcuts

- Comparing only `ConversationState.revision` when it can remain unchanged for a message; storage version must be separate.
- Last-write-wins overwrite of a newer session.
- Generating a new audit event ID on every retry.
- Treating an audit duplicate as a second business revision.
- Replaying an entire user turn automatically after a conflict without an explicit idempotency/concurrency policy.
- Reading chat history and inferring state instead of loading the structured snapshot.

## Error semantics

- Missing session: `load` returns `None`; create requires `expected_storage_version=None`.
- Stale version/existing create: typed `SessionConcurrencyError`; no write occurs.
- Serialization, filesystem, permission, or backend outage: typed persistence error; partial writes are not reported as success.
- Duplicate same-ID same-payload audit: success/no-op.
- Duplicate same-ID different-payload audit: typed audit conflict.
- Audit delivery failure after session save: state remains persisted; caller exposes retryable audit status without rolling back business state.

## Status semantics

Persistence does not invent workflow statuses. A conflict or backend failure is an application/API error that later turn-completion code maps to a safe response; the stable workflow outcome remains the one produced before persistence.

## Schema revision semantics

The storage version is independent of Forge `schema_revision`. Both must be preserved in persisted workflow state, and neither is included in `ContractDraft.canonical_hash()`.

## Rendering semantics

Persist stable draft hash, schema revision, final-validation receipt, and artifact identity as application state if needed for reuse. The audit/session adapters do not call `render_yaml`.

## Template semantics

Persist runtime DSL values verbatim and never render/translate them in storage or audit adapters.

## Arrays and paths

Session serialization must round-trip nested dict/list `ContractDraft.values` and concrete instance paths without flattening or wildcard conversion. Version conflicts must preserve the complete nested snapshot.

## Value precedence

No precedence decision belongs to persistence/audit. Candidate and resolution history is serialized as produced by ADCM, including selected IDs, origins, scope/rule metadata on candidates, and superseded statuses.

## Tests

- **Unit:** version increment, create-if-absent, deep-copy isolation, malformed JSON, atomic-write failure, and idempotent JSONL append.
- **Concurrency negative:** stale writer cannot overwrite; same session with two expected versions yields exactly one success.
- **Audit contract:** duplicate identical ID is a no-op; same ID/different payload is rejected; retries reuse the original ID.
- **Integration:** business revision history and storage version evolve independently; nested arrays and schema revisions survive reload.
- **Privacy:** audit payload excludes hidden reasoning/secrets and records only safe domain decisions/boundary metadata.

## Acceptance criteria

- Repository load/save exposes and enforces an explicit storage version.
- Memory and JSON adapters pass the same version/conflict contract.
- Audit sinks are idempotent by event ID and detect divergent duplicate payloads.
- A stale save cannot change the persisted draft, candidates, revisions, or workflow state.
- No database migration root, event-sourcing framework, or implicit last-write-wins behavior is introduced.

## Explicit non-goals

HTTP idempotency keys and conflict response mapping, read-only UI, Forge transport, and release infrastructure are later stages. This stage does not define cross-process locking guarantees beyond the selected adapter's documented atomic write behavior.

## Documentation updates

Update `docs/ADAPTERS_AND_DEPLOYMENT.md`, `docs/TURN_LIFECYCLE.md`, `docs/DESIGN_DECISIONS.md`, session/audit port symbol docs, and any architecture module pages impacted by the new versioned boundary.

## Completion checklist

- [ ] Storage version is separate from business revision.
- [ ] Stale writes fail without data loss or silent merge.
- [ ] JSON/memory adapters share the same contract.
- [ ] Audit append is idempotent and conflict-aware.
- [ ] Persistence/audit errors and privacy boundaries are tested.
- [ ] No migration/deployment framework was added.

