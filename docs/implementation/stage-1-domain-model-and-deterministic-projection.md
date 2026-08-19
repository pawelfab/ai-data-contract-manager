# Stage 1 — Domain model, provenance, deterministic resolution, paths, and projection

## Goal

ADCM has a complete, framework-independent domain boundary for evidence, signals, preferences, value candidates, resolved values, nested drafts, schema views, revisions, and rendering/workflow tokens. A candidate can be selected deterministically without UUID ordering, user-origin data cannot cross the binder without evidence, and `DraftProjector` can rebuild an authorized nested JSON/YAML draft—including concrete array instances—from resolved values.

## Why this stage exists

The current domain already contains most of these models, but the invariants are spread across Pydantic validators and application helpers. The workflow and future transports need one unambiguous contract before they can be changed. This stage isolates domain correctness from Forge transport, NLP, HTTP, and persistence so later failures cannot be hidden by changing business state representation.

## Preconditions

- Stage 0 has classified contract artifacts and has not introduced an ADCM schema evaluator.
- `src/adcm/domain` remains independent of Pydantic AI, MCP transports, persistence, and web frameworks.
- The canonical enums and stateless request/response models in `src/adcm/domain/models.py` are available for extension rather than replaced by parallel models.
- The implementer accepts the existing nested `ContractDraft.values` representation and the `{}` padding behavior for intermediate list-of-object elements.

## Scope

- Confirm and, where needed, complete `Evidence`, `Signal`, `Preference`, `ValueCandidate`, `ResolvedValue`, `ContractDraft`, `CurrentSchemaView`, revision, capability, validation, render, and workflow models.
- Keep user-origin Evidence validation strict and preserve provenance fields (`evidence_ids`, source signal/preference IDs, rule ID, scope, priority, revision, sequence).
- Define deterministic candidate ranking: explicit priority/origin priority first, then revision and candidate sequence for same-origin corrections, with confidence only as an explicit final policy tie-break. UUIDs are never a business tie-breaker.
- Keep candidate-only metadata such as Forge `scope` and `rule_id` on `ValueCandidate`; `ResolvedValue` contains the selected candidate ID and resolved value/origin/evidence.
- Keep `ContractPath` as the concrete instance-path parser/reader/writer and `CurrentSchemaView.is_path_allowed` as the authorization check (exact paths plus indexed wildcard paths).
- Make projection a full rebuild from resolved values and the current view; illegal historical values disappear from the current draft without deleting history.
- Add focused tests for invariants, corrections, arrays, wildcard authorization, canonical hashing, and status enums.

## Out of scope / Do not do

- Do not call Forge, an external MCP, an LLM, or a persistence store from the domain package.
- Do not flatten `ContractDraft` into `dict[path, value]` or serialize concrete list indices as schema wildcards.
- Do not add event sourcing, CQRS, Kafka, Temporal, a repository-per-entity, or a service locator.
- Do not add workflow loops, HTTP models, response composition, or provider-specific settings here.
- Do not relax the evidence validator for binder-created candidates or move provenance to `ResolvedValue`.

## Architectural boundaries

- **ADCM domain:** owns typed state and invariant enforcement; it does not decide whether a path is legal without a Forge-provided `CurrentSchemaView`.
- **Contract Forge:** later supplies `AllowedPath`, requirements, Forge candidates, rule priority/specificity, and schema revisions.
- **LLM:** may propose schema-agnostic semantics later; it cannot construct or select a `ResolvedValue` directly.
- **Other MCPs:** their results enter as capability/evidence/candidate inputs through application ports, never as draft mutations.
- **Airflow DAG Generator:** consumes preserved runtime DSL later; domain models must treat such strings as opaque values.

## Invariants

- No `ResolvedValue` exists without a selected `ValueCandidate` with the same path, value, origin, and evidence IDs.
- Every `ValueCandidate` has an origin; USER_EXPLICIT and USER_PREFERENCE candidates require evidence.
- Every candidate ID is unique within aggregate state, and optional confidence is finite.
- USER_EXPLICIT `Signal` and USER_PREFERENCE `Preference` require evidence; a signal may remain unbound and pathless.
- Preferences may expand to zero, one, or many currently legal paths.
- Corrections supersede old records without deleting them.
- `CurrentSchemaView` is a replaceable snapshot, not an accumulating set.
- `ContractDraft` stores nested data and supports arrays; schema paths and instance paths remain distinct.
- Candidate tie-breaking is deterministic and never uses UUID ordering; duplicate IDs and non-finite confidence are invalid, and a policy-rank tie after confidence is rejected rather than resolved by candidate metadata.

## Files affected

| File | Action | Purpose |
|---|---|---|
| `src/adcm/domain/models.py` | MODIFY | Finalize validators, enum values, nested draft models, revision/sequence fields, and stateless Forge boundary types. |
| `src/adcm/domain/contract_path.py` | MODIFY if required | Preserve parsing, nested writes/reads, indexed arrays, and intentional `{}` padding. |
| `src/adcm/application/candidate_resolver.py` | MODIFY | Implement the documented deterministic ranking and status updates. |
| `src/adcm/application/draft_projector.py` | MODIFY | Rebuild only currently authorized nested paths. |
| `src/adcm/application/signal_binder.py` | MODIFY | Propagate origin/evidence/source IDs without fabricating provenance. |
| `src/adcm/application/preference_expander.py` | MODIFY | Expand active preferences only to current `AllowedPath.concepts`. |
| `tests/test_candidate_resolver.py` | MODIFY | Cover precedence, scope placement, and revision/sequence corrections. |
| `tests/test_contract_path.py` | MODIFY | Cover nested objects, arrays, reads, invalid shapes, and `{}` padding. |
| `tests/test_draft_projector.py` | MODIFY | Cover unauthorized paths and current-view reprojection. |
| `tests/test_signal_binding.py` | MODIFY | Cover evidence and ambiguity invariants. |
| `tests/test_revisions.py` | MODIFY | Cover supersession without deletion and revision records. |
| `docs/DOMAIN_MODEL.md` | MODIFY | Synchronize current domain contracts and invariants. |
| `docs/DESIGN_DECISIONS.md` | MODIFY | Record any resolved domain ambiguity. |

## Public contracts

The following existing symbols are the public contract; extend them rather than creating parallel abstractions:

- `Evidence`, `Signal`, `Preference`, `ValueCandidate`, and `ResolvedValue` in `adcm.domain.models`.
- `ContractDraft(values: dict[str, Any], revision: int)` with `canonical_hash()` based only on canonical draft content.
- `CurrentSchemaView(schema_revision, stage_id, allowed_paths)` with exact/indexed-wildcard `is_path_allowed(path)`.
- `ContractPath.parse`, `ContractPath.write(document, path, value)`, and `ContractPath.read(document, path, default=None)`.
- `CandidateResolver.resolve(candidates) -> dict[str, ResolvedValue]`.
- `DraftProjector.project(resolved, schema_view, revision) -> ContractDraft`.
- `SignalBinder.bind(signals, allowed_paths) -> list[ValueCandidate]` and `PreferenceExpander.expand(preferences, allowed_paths) -> list[ValueCandidate]`.

Canonical status values remain exactly:

- evaluation: `INCOMPLETE`, `COMPLETE`, `INVALID`;
- finding: `VALID`, `INVALID`, `DEFERRED`;
- final validation: `VALID`, `INVALID`, `DEFERRED_EXTERNAL`;
- workflow outcome: `WAITING_FOR_USER`, `BLOCKED_EXTERNAL`, `COMPLETE`, `INVALID`, `FAILED`.

## Inputs and outputs

Inputs are typed domain records and a Forge-owned `CurrentSchemaView`. Outputs are new or updated candidates, deterministic `ResolvedValue` records, and a newly built nested `ContractDraft`. History collections remain available for audit and correction; no application service receives a flat path map as authoritative state.

## State ownership

`ConversationState` (owned by ADCM) stores evidence, signals, preferences, candidates, resolutions, draft, workflow tokens, messages, revisions, and audit events. Domain helpers are pure or mutate only the records explicitly passed to them. Forge-owned rule storage and LLM conversation context do not cross into these models as hidden state.

## Data flow

```text
Evidence -> Signal/Preference -> ValueCandidate
                                 -> deterministic resolver
                                 -> ResolvedValue map
CurrentSchemaView + ResolvedValue map
                                 -> DraftProjector/ContractPath
                                 -> nested ContractDraft
```

## Required behavior / how it should work

1. Reject user-origin signals, preferences, and candidates that lack evidence IDs at model validation time.
2. Permit pre-path signals to remain `unbound`; bind only when exactly one current allowed path advertises the concept. Ambiguous or absent matches remain unbound and do not create a candidate.
3. Copy evidence IDs and source identifiers from a signal/preference into its candidate. The binder/expander must never invent Evidence or change origin.
4. Preserve all non-rejected/non-superseded candidates, select one per concrete path, and expose the winner through `selected_candidate_id`. Preflight and compute every winner before changing statuses so any error leaves all candidates unchanged.
5. Rank explicit Forge priority and ADCM origin precedence deterministically; use `created_revision` and `sequence` for same-origin corrections, with confidence as the final policy tie-break. Candidate order, UUID values, value content, scope, rule ID, and reason must not change the winner; a tie after confidence is rejected as invalid candidate state.
6. Rebuild a fresh document on every projection. Write only paths accepted by `CurrentSchemaView`; use concrete indices for arrays and preserve `{}` padding when an intermediate list of objects skips indices.
7. `ContractDraft.canonical_hash()` hashes only canonical nested content. `schema_revision` is tracked separately and is never inserted into the hash.

## Forbidden implementation shortcuts

- Selecting a winner with `max(..., key=candidate.id)` or any UUID ordering.
- Mutating `ContractDraft` from `SignalBinder`, an LLM result, or a capability result.
- Treating `scope` as a property of `ResolvedValue` or dropping the selected candidate link.
- Unioning allowed paths from old and new schema views.
- Writing `None` padding solely to satisfy a fixture that expects `{}` for object arrays.
- Treating a schema wildcard (`[*]`) as a concrete list index when writing the draft.

## Error semantics

- Pydantic validation errors identify missing Evidence/origin and are domain-invalid state.
- `ContractPath` raises `ValueError` for malformed paths and `TypeError` for incompatible object/list shapes; reads may return their requested default.
- Projection silently omits resolved values unauthorized by the current view (and tests must prove the omission); it must not broaden authorization.
- Candidate resolution must have deterministic behavior for all valid inputs; an empty candidate set yields an empty resolution map.
- A policy-rank tie after confidence raises `ValueError`; it must be resolved by the producer through priority, revision, sequence, or confidence rather than candidate metadata.
- Duplicate candidate IDs, non-finite confidence, and any per-path policy tie raise deterministic errors before any candidate status is changed.
- Resolution/candidate values use strict canonical JSON equality, not Python equality; booleans, integers, and floats remain distinct canonical values.

## Status semantics

This stage defines the enum vocabulary but does not map Forge calls to `WorkflowOutcome`. No top-level `DEFERRED` evaluation status may be introduced.

## Schema revision semantics

`CurrentSchemaView.schema_revision` is an opaque Forge token carried by state. It is not part of `ContractDraft.canonical_hash()` and is not generated by domain helpers.

## Rendering semantics

Domain models may carry `RenderMode`, `RenderRequest`, `RenderedContract`, and `FinalValidationReceipt`, but this stage does not call `render_yaml` or cache artifacts.

## Template semantics

Values are opaque. Neither domain validation nor path projection may consume `{source}` or runtime `{{...}}` template strings.

## Arrays and paths

Schema paths such as `silver.tables[*].columns` describe authorization patterns. Instance paths such as `silver.tables[0].columns[2].name` address concrete values. `ContractPath.write` must create the nested list/object shape and may use `{}` for skipped object-list positions. Projection must accept an instance path only when its wildcard-normalized form is authorized.

## Value precedence

ADCM origin precedence is deterministic (`USER_EXPLICIT` above user preference, existing/external values, MCP enrichment/derived/default according to the canonical map). Forge supplies explicit priority/specificity for conflicts among its own candidates. The LLM never selects the winner. Candidate `scope` and `rule_id` remain candidate metadata.

## Tests

- **Unit/domain:** Evidence validators, enum values, canonical hash independence from schema revision, and rejected malformed paths.
- **Unit/application:** deterministic user/enrichment/default precedence; system versus generic rule priority; same-origin correction by revision/sequence; selected candidate metadata location.
- **Negative:** user signal/candidate without evidence; ambiguous concept binding; unauthorized projection; incompatible array/object writes.
- **Contract:** schema wildcard authorization against concrete indices and nested array round trips.
- **Regression:** corrections supersede history and preserve old records; no UUID-based tie behavior.

## Acceptance criteria

- All listed public models and helpers have tests for the stated invariants.
- Reordering candidates or regenerating UUIDs does not change a same-origin winner when revision/sequence are unchanged.
- A projection after a schema-view branch change contains no illegal historical paths while the candidate/signal history remains present.
- Nested arrays round-trip through `ContractPath` and canonical hashing is stable for equivalent key order.
- No import from `adcm.domain` reaches Pydantic AI, MCP, persistence, YAML, or web framework code.

## Explicit non-goals

Forge rule compilation/transport, fast-forward orchestration, semantic parsing, durable versioning, HTTP/UI, and real-contract integration are later stages.

## Documentation updates

Update `docs/DOMAIN_MODEL.md`, `docs/architecture/modules/domain.md`, `docs/architecture/symbols/domain.md`, `docs/architecture/modules/application.md`, and `docs/DESIGN_DECISIONS.md` for any changed public symbol or invariant. Keep generated architecture files as navigation aids only.

## Completion checklist

- [x] Domain models and validators match the canonical invariant list.
- [x] Candidate ranking is deterministic and UUID-independent.
- [x] Evidence/provenance is preserved through binding and resolution.
- [x] Nested array paths and current-view projection are covered by tests.
- [x] Domain dependency direction remains clean.
- [x] No workflow/provider/UI code was added.
