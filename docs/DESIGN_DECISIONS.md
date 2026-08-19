# Design decisions

## Schema is authority
LLM semantics never authorize contract paths. DraftProjector only accepts paths in the current Forge schema view.

## ADCM stateful, Forge stateless
ADCM owns sessions, evidence, candidates, revisions and draft. Forge evaluates a supplied snapshot and does not keep onboarding sessions.

## Current view replaces old view
Allowed paths are not accumulated. This enables safe branch corrections and draft reprojection.

## Draft is nested JSON/YAML shape
Path strings are addressing metadata, not the storage format of ContractDraft.

## Candidate provenance is not copied into ResolvedValue
`ResolvedValue.selected_candidate_id` points to the winning candidate. Candidate scope/rule metadata remains on the candidate.

## User evidence invariant is strict
USER_EXPLICIT signals and candidates require evidence. SignalBinder never fabricates evidence and never changes origin to bypass validation.

## Forge vs ADCM precedence
ADCM resolves origins (user, preference, external, MCP enrichment/default). Forge owns conflicts among Forge rules and should return explicit priority/specificity metadata.

ADCM origin precedence is applied before Forge rule priority, so a Forge rule cannot override a
user-origin candidate by declaring a larger number. Within one origin, rule priority is followed
by correction revision and sequence; UUIDs are never used to choose a value. A complete
policy-rank collision after confidence is rejected as ambiguous, because selecting either candidate's evidence
would otherwise make the result depend on input order.

Candidate confidence must be finite; the model rejects NaN and infinity, and the resolver repeats
the guard for mutated or otherwise bypassed model instances. Candidate UUIDs are identifiers only:
duplicates are invalid and are rejected before any selection status changes. Aggregate state permits
at most one `selected` candidate per concrete path.

Resolver execution has a preflight/commit boundary. It validates every candidate and computes every
per-path winner before constructing resolutions and changing statuses. Therefore an invalid candidate
or tie on a later path cannot leave earlier paths partially selected.

Resolved/candidate values are compared through the same strict canonical JSON representation used
for draft hashing. Python equality is insufficient because booleans compare equal to integers and
integer/float equality can hide distinct canonical JSON content.

## Concrete projection paths
`AllowedPath` may contain a schema wildcard (`[*]`), but candidate binding and projection use
only concrete paths accepted by `ContractPath.parse`. The wildcard pattern authorizes indexed
instances; it is never passed to the nested draft writer. A changed schema view can therefore
return a previously bound signal to `unbound` without removing its history. The dict-backed draft
does not support a root-list path such as `[0].name`.

## Status ownership
Forge describes contract state. ADCM describes orchestration state. Therefore Forge never returns WAITING_FOR_USER/BLOCKED_EXTERNAL.

## Deferred validation
Forge returns deferred findings/dependencies. ADCM obtains missing capabilities/values and invokes Forge again. There is no background resume in Forge.

## Schema revision consistency
Forge returns schema revision; ADCM sends it back as `expected_schema_revision`. Render cache key includes schema revision separately from draft hash.

## Rendering
Forge owns canonical YAML. `render_yaml` is separate from `evaluate_draft`; render once after turn stabilization when the artifact key changed.

## Template ownership
Forge resolves `{source}`-style enrichment placeholders but preserves `{{...}}` runtime Contract DSL. Airflow DAG Generator translates runtime DSL later.

## Repository ownership
Production `contract.json` and enrichment rules belong to Contract Forge. ADCM may keep fixtures for tests only.

For migration tests, the repository-approved fixture is `contracts/contract.json`; the
retired `contracts/data-contract.schema.json` filename must not be recreated. This path
decision only selects a local test fixture and does not identify a production schema source.

## Stage-plan baseline (2026-08-19)

`IMPLEMENTATION_PLAN.md` at the repository root is the canonical short roadmap. The former nine-item recommendation in `docs/IMPLEMENTATION_ROADMAP.md` is numbered as Stages 0–8; detailed contracts live under `docs/implementation/`.

The current `contracts/contract.json` is a migration/reference artifact, not evidence that ADCM owns the production schema. Its converter/preparator component definitions are now reachable from the root; several unrelated imported legacy rule definitions remain migration-only and are not part of the active root graph. No stage may claim production ownership for ADCM from the local copy.

`contracts/ux_rules.json` now contains the owner-requested local enrichment definitions for ROCKET and SAP. It is still a Contract Forge input/fixture, not an ADCM evaluator or proof of production deployment. Contract Forge integration remains blocked until the production source location/endpoint and transport contract are identified. Documentation examples are not a license to reconstruct additional business rules.

`Settings` can select `mock`, `fixture`, or `remote` Forge configuration. The default
remains `mock`; fixture and remote selections retain opaque source references, and remote
selection also requires an endpoint. Settings never open, parse, cache, or evaluate a
schema or enrichment artifact. A configured remote target is not evidence that the missing
production transport contract has been supplied, so Stage 3 remains `BLOCKED_INPUT`.

Audit may contain explicit domain decisions and redacted boundary payloads. It must never claim to capture or persist hidden model reasoning/chain-of-thought, even when model I/O auditing is enabled.

No stage introduces a database-migration root or deployment manifest without a separate, explicit repository decision.
