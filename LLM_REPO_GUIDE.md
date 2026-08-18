# LLM repository guide

Read this before changing the repository.

## What ADCM is
A typed conversational orchestrator around Contract Forge and future MCP capabilities. It is deliberately small. Deterministic application code owns state and workflow; Pydantic AI is only the semantic interpreter adapter.

## Hard boundaries
- ADCM owns session/chat/evidence/signals/preferences/candidates/revisions/audit/orchestration.
- Contract Forge owns schema, canonical paths, requirements, defaults, enrichment rules, validation and YAML serialization.
- LLM does not authorize paths and does not choose candidate precedence.
- External MCPs return capability results; they never mutate draft.

## Current Forge API direction
Stateless operations:
- `evaluate_draft(ContractInput)`
- `validate_final(ContractInput)`
- `render_yaml(RenderRequest)`

Do not reintroduce stateful Forge sessions or `submit_values(session_id, ...)`.

## Status semantics
`evaluate_draft`: INCOMPLETE / COMPLETE / INVALID.
Individual findings: VALID / INVALID / DEFERRED.
`validate_final`: VALID / INVALID / DEFERRED_EXTERNAL.
ADCM outcome: WAITING_FOR_USER / BLOCKED_EXTERNAL / COMPLETE / INVALID / FAILED.

## CurrentSchemaView
Replace it on every Forge call. Never union historical allowed paths. DraftProjector always rebuilds the nested draft from current resolved values and the current view.

## Provenance
USER_EXPLICIT Signal and ValueCandidate require evidence. Binder propagates provenance; it does not fabricate it. Candidate-specific metadata such as rule scope stays on ValueCandidate.

## Corrections
Do not delete history. Supersede old Signals and candidates. Same-priority resolution must use deterministic revision/sequence, never UUID ordering.

## Arrays
ContractDraft stores actual nested data. `ContractPath` addresses concrete instance paths. Do not regress to a flat `dict[path,value]` draft.

## Templates
Forge resolves `{source}` enrichment-time placeholders only. Preserve runtime DSL: `{{env}}`, `{{date:%Y%m%d}}`, `{{var.name}}`. Airflow DAG Generator translates them later.

## Rendering
Do not render YAML after every internal Forge iteration. Fast-forward may evaluate Forge several times in one turn. Render after stabilization and cache by `(draft_hash, schema_revision, render_mode)`.

## Before implementation
Read `docs/ISSUES_AND_RESOLUTIONS.md`, `docs/ARCHITECTURE.md`, `docs/DOMAIN_MODEL.md`, `docs/MCP_CONTRACT.md`, `docs/DESIGN_DECISIONS.md` and the relevant stage specification.

## Do not over-engineer
Do not add CQRS/Event Sourcing/Kafka/Temporal/multi-agent/DI containers without a concrete requirement.
