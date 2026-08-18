# Issues and resolutions discovered during design and Stage 2

This document records the problems found during analysis and implementation, the chosen resolution, and the architectural rule that follows from it.

## Contract / Forge issues

### R-01 — rule paths snake_case vs schema camelCase
**Problem:** `x-contract-rules` may reference aliases such as `source.source_type`, while schema properties are canonical camelCase.

**Resolution:** Contract Forge owns path normalization/compilation. It must convert rule paths to canonical schema paths before evaluation and fail configuration loading on unknown or ambiguous aliases. ADCM sees canonical paths only.

### R-02 / R-03 — conflicting defaults and system enrichments without precedence
**Problem:** multiple rules can produce candidates for the same path.

**Resolution:** preserve all candidates with provenance. ADCM owns origin precedence (user > MCP enrichment > MCP default etc.). Forge owns precedence between Forge rules and should return explicit rule priority/specificity metadata. `scope` remains metadata on `ValueCandidate`, not on `ResolvedValue`.

### R-04 — preparator default activates another required field
**Problem:** a default such as `preparator.enabled=true` can activate a contract rule that requires an operation.

**Resolution:** defaults are candidates, not unconditional writes. Forge reevaluates rules after the value is applied. If a new required field has no candidate, ADCM eventually asks the user. Do not silently flip the default to make validation pass.

### R-07 / R-08 / R-09 — template semantics
The contract intentionally has two rendering phases.

**Enrichment-time placeholders**, e.g. `{source}`, are resolved by Forge.

**Runtime Contract DSL**, e.g. `{{env}}`, `{{date:%Y%m%d}}`, `{{var.name}}`, is preserved by Forge and later translated by the Airflow DAG Generator. `{{date:%Y%m%d}}` is not an accidental second date dialect; it is the contract DSL. The critical invariant is that Forge must not consume `{{...}}` while resolving `{...}`.

### R-10 — source-specific token inside a global default
**Resolution:** move the rule to the system-specific layer or parameterize it with an enrichment-time placeholder. Do not add ADCM special cases.

### R-11 — `ensure_list_item` creates an incomplete list item
**Resolution:** this is a workflow concern, not a reason to fake required values. Creating an item activates its required fields; user / enrichment / Schema Explorer may fill them later.

### R-12 — `env` referenced by templates but not in contract schema
**Resolution:** if `{{env}}` is runtime DSL consumed by the DAG Generator, ADCM and Forge do not need the concrete env value at onboarding time. It is not a ContractDraft value and does not need a ContextFact. Only introduce external context if a Forge decision truly depends on the concrete environment during onboarding.

### R-13 — registry validation unavailable locally
**Resolution:** validation finding supports `VALID | INVALID | DEFERRED`. Deferred findings include dependencies. ADCM attempts to satisfy capabilities and calls Forge again. Forge does not run background retries and does not call external MCPs directly.

### R-16 — `systems.<sys>.source_types` is not enforced
**Resolution:** Forge must expose/validate allowed values. ADCM must not infer this rule from enrichment JSON.

### R-17 / R-18 — redundant or asymmetric rules
**Resolution:** remove redundant rules only after confirming semantic equivalence. Do not force symmetry of defaults unless it is a real business rule.

### R-19 — README referenced missing documentation
**Resolution:** repair documentation links immediately. LLM coding agents treat repository docs as operational architecture, so stale links are not cosmetic.

### R-20 — contract and enrichment files placed in ADCM
**Resolution:** production ownership belongs to Contract Forge. Local copies may exist only as test fixtures during migration. Record the repository ownership decision in `DESIGN_DECISIONS.md`.

## ADCM domain/workflow issues

### R-05 — allowed paths were accumulated forever
**Problem:** changing an earlier discriminator such as CSV -> Parquet could leave CSV-only fields legal in the draft.

**Resolution:** Forge returns a `CurrentSchemaView`. ADCM replaces the view on every evaluation; it never accumulates allowed paths. `DraftProjector` rebuilds the draft from resolved values and the current view. Historical signals/candidates remain, but illegal fields disappear from the current draft.

### R-06 — USER_EXPLICIT vs USER_EXPLICIT tie was UUID-based
**Resolution:** deterministic ranking uses priority, `created_revision`, and candidate sequence. Corrections supersede old signals and their candidates. UUID is never a business tie-breaker.

### R-14 — flat draft could not represent arrays
**Resolution:** `ContractDraft.values` stores the real nested JSON/YAML structure. `ContractPath` handles concrete instance paths such as `silver.tables[0].columns[2].name`. Schema paths such as `silver.tables[*].columns` remain distinct from instance paths.

### R-15 — tests depended on fake schema paths
**Resolution:** separate domain/workflow tests from real-contract integration tests. Workflow tests use deterministic fake semantics. Real schema behavior belongs to contract integration tests.

## Stage 2 implementation failures

### `ContractPath.write` padded intermediate object arrays with `{}` instead of `None`
The test expectation was wrong for a list of objects. Example:

```json
{"silver":{"tables":[{},{},{"source":"x"}]}}
```

is correct when writing `silver.tables[2].source`. A future schema-aware writer may specialize padding for scalar arrays, but Stage 2 must not over-expand scope.

### `SignalBinder` created USER_EXPLICIT candidates without evidence
**Resolution:** do not relax the invariant and do not fabricate evidence in the binder. User-origin `Signal` itself requires `evidence_ids`. `SignalBinder` only propagates origin, evidence and `source_signal_id` into the candidate. A manually constructed user Signal without evidence is invalid test/domain state.

### test expected `ResolvedValue.scope`
**Resolution:** `scope` describes the candidate/rule that produced a value and stays on `ValueCandidate`. `ResolvedValue` references `selected_candidate_id`; tests inspect the winning candidate when they need scope/provenance details.

### fast-forward test stopped before `metadata.id`
**Cause:** the demo interpreter recognized `średnik` but not ASCII `srednikiem`, so delimiter was missing and the workflow correctly stopped earlier.

**Resolution:** demo interpreter folds diacritics. More importantly, WorkflowRunner tests use a deterministic fake interpreter returning structured `TurnInterpretation`; NLP parsing is tested separately.

## Stateless Forge contract

Forge is stateless. ADCM sends the current contract snapshot on every call.

```text
evaluate_draft(ContractInput)
validate_final(ContractInput)
render_yaml(RenderRequest)
```

`ContractInput` contains the current draft, capability results, and optional `expected_schema_revision`. It does not contain ConversationState, chat history, evidence history, signals or superseded candidates.

### Status ownership

`evaluate_draft.status`:
- `INCOMPLETE`
- `COMPLETE`
- `INVALID`

Individual validation findings:
- `VALID`
- `INVALID`
- `DEFERRED`

`validate_final.status`:
- `VALID`
- `INVALID`
- `DEFERRED_EXTERNAL`

ADCM `WorkflowOutcome.status`:
- `WAITING_FOR_USER`
- `BLOCKED_EXTERNAL`
- `COMPLETE`
- `INVALID`
- `FAILED`

Forge never returns `WAITING_FOR_USER` or `BLOCKED_EXTERNAL`; only ADCM knows whether a missing dependency can be satisfied from signals, preferences, another capability, or only by the user.

## Schema revision and rendering

Forge returns `schema_revision` in `CurrentSchemaView`. ADCM sends it back as `expected_schema_revision` on subsequent evaluate/validate/render calls. A schema change must not be silently accepted mid-workflow.

`draft_hash` hashes only the canonical draft. Artifact cache key is:

```text
(draft_hash, schema_revision, render_mode)
```

`RenderMode` has exactly:
- `DRAFT`
- `FINAL`

`FINAL` is allowed only after `FinalValidationStatus.VALID` for the same draft and schema revision.

Rendering is not attached to every Forge evaluation. The fast-forward/deferred loop is allowed to call Forge many times in one user turn. `render_yaml` is called once after turn stabilization, and only if the artifact cache key changed.
