# ADCM architecture

## Core responsibility split

**LLM / Pydantic AI** handles semantics only: intent, extraction, corrections, ambiguity, typo suggestions and semantic binding proposals.

**ADCM** owns state and orchestration: chat/session, signals, preferences, evidence, revisions, candidates, resolution, current draft, capability routing, fast-forward and presentation state.

**Contract Forge** owns contract authority: schema, canonical paths, progressive schema view, requirements, defaults, enrichments, rule evaluation, validation and YAML rendering.

**Other MCPs** expose capabilities (Schema Explorer, repository lookup, registry etc.). They never mutate ContractDraft directly.

## Core data flow

```text
User message
  -> Evidence
  -> Signal / Preference
  -> ValueCandidate
  -> ResolvedValue
  -> DraftProjector + CurrentSchemaView
  -> ContractDraft
```

Schema is authoritative. A Signal can exist without a path. A path cannot enter the draft unless the current Forge schema view authorizes it.

## Stateful ADCM / stateless Forge

Forge does not maintain an onboarding session. ADCM sends a current snapshot:

```text
ADCM state
 -> ContractDraft snapshot
 -> Forge.evaluate_draft()
 -> schema view + requirements + candidates + findings + capability requests
 -> ADCM resolves/updates state
 -> Forge.evaluate_draft() again if progress was made
```

The loop ends only when the turn is stable: user input is required, an external dependency is blocked, validation is invalid, or final validation is valid.

## CurrentSchemaView and reprojection

`CurrentSchemaView` is replaced on every Forge response. ADCM does not union old `allowed_paths` with new ones. This is required for corrections that change the active branch.

Example: CSV -> Parquet removes CSV-only delimiter paths from the current schema view. Historical evidence and candidates remain; `DraftProjector` rebuilds the current draft and drops paths that are no longer legal.

## Capability routing

Forge may return a `CapabilityRequest`. ADCM routes it to the relevant adapter/MCP, stores a `CapabilityResult`, and calls Forge again. Forge itself never calls Schema Explorer or other MCPs.

## Rendering

Draft preview is an ADCM read model. Canonical YAML is rendered by Forge.

Forge rendering is a separate operation from evaluation. Multiple internal evaluations may happen in one user turn; YAML is rendered only after stabilization and only for a new artifact key:

`draft_hash + schema_revision + render_mode`.

`RenderMode = DRAFT | FINAL`. FINAL requires a VALID final-validation result for the same draft/schema.

## Template boundary

Forge resolves enrichment-time placeholders such as `{source}`. It preserves runtime contract DSL such as `{{env}}`, `{{date:%Y%m%d}}`, and `{{var.name}}`. The Airflow DAG Generator later translates that DSL to Airflow/Jinja.
