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
