# Stage 0 — Repository baseline, configuration, and Contract Forge artifact ownership

## Goal

After this stage the repository has an evidence-backed baseline and an explicit ownership boundary for every contract artifact. ADCM can select a Forge transport from configuration, but it does not parse or evaluate the production schema. `contracts/contract.json`, `contracts/ux_rules.json`, and `examples/contract-rules.json` are classified as migration/reference inputs until the Forge owner confirms the production source and transport. The production Forge endpoint remains an explicit blocker for Stage 3 rather than being inferred from local fixtures.

## Why this stage exists

The current tree contains a useful JSON Schema, a local `contracts/ux_rules.json` bundle, a legacy rule catalog, a staged mock Forge, and an artifact test that uses the canonical `contracts/contract.json` path. It does not identify a production Forge implementation or transport contract. Later stages must not silently turn these fixtures into a second schema engine inside ADCM. Establishing the baseline first makes the remaining work reviewable and prevents implementation from being based on stale or unreachable rules.

## Preconditions

- Python 3.11+ and the existing `pyproject.toml` test configuration are available.
- The repository root, `src/adcm`, `tests`, `contracts`, `examples`, and `docs` are present.
- The implementer has read `LLM_REPO_GUIDE.md`, `docs/ISSUES_AND_RESOLUTIONS.md`, and this stage contract.
- `contracts/contract.json` and `examples/contract-rules.json` can be loaded as UTF-8 JSON.
- If the owner has not supplied an authoritative Forge source/endpoint and transport contract, Stage 3 must be reported as `BLOCKED_INPUT`; the local UX bundle is not a substitute for those inputs.

## Scope

- Produce a verified inventory of the current schema, reachable `$defs`, `x-contract-rules`, examples, and enrichment inputs.
- Preserve the existing `Settings` configuration boundary and add only explicit transport/source settings needed to select a mock, local fixture, or remote stateless Forge. Configuration must not load or evaluate schema rules in ADCM.
- Record that production ownership of `contract.json` and enrichment rules belongs to Contract Forge. Local copies may remain as test fixtures during migration.
- Resolve the schema-test path decision explicitly: either restore the owner-approved fixture name or update `tests/test_contract_schema_rules.py` to the owner-approved artifact. Do not make the test pass by copying or rewriting rules without that decision.
- Keep `MockContractForgeAdapter` clearly labelled as test/demo behavior and keep the logical three-operation Forge port unchanged.
- Update ownership/baseline documentation and the short roadmap links when paths or statuses change.

## Out of scope / Do not do

- Do not implement a JSON Schema parser, `x-contract-rules` evaluator, enrichment evaluator, alias compiler, or YAML renderer in `src/adcm`.
- Do not evaluate `contracts/ux_rules.json` or copy the legacy rule catalog into an ADCM runtime module; these remain Forge-owned artifacts/fixtures.
- Do not add a stateful `submit_values(session_id, ...)` Forge API.
- Do not add HTTP, UI, persistence migrations, deployment manifests, or production MCP clients in this stage.
- Do not change the meaning of the reachable `contracts/contract.json` schema merely to satisfy the stale test path.

## Architectural boundaries

- **ADCM:** owns configuration selection and treats local contract files as opaque fixtures; it owns session/workflow state, not schema authority.
- **Contract Forge:** owns the production `contract.json`, canonical paths, progressive requirements, defaults, enrichments, rule evaluation, validation, and YAML serialization.
- **LLM:** has no role in artifact loading or validation; it may only interpret user language through the semantic port in later stages.
- **Other MCPs:** are not called here and never mutate `ContractDraft`.
- **Airflow DAG Generator:** is not involved; runtime Contract DSL remains a later Forge output concern.

## Invariants

- No ADCM draft path is legal without current Forge authorization.
- ADCM and external MCP/LLM output never mutate `ContractDraft` directly.
- Contract schema and Forge rules outrank semantic inference.
- Unknown system-specific enrichment must not break generic onboarding.
- Contract-specific paths are not hardcoded into ADCM application logic.
- Production schema/enrichment ownership is not transferred to ADCM by keeping a fixture in this repository.

## Files affected

| File | Action | Purpose |
|---|---|---|
| `src/adcm/config.py` | MODIFY | Expose the minimal typed transport/source selection needed by the composition root; keep defaults pointing at the mock/reference adapter. |
| `src/adcm/ports/contract_forge.py` | MODIFY only if required | Keep the stateless `evaluate_draft`, `validate_final`, and `render_yaml` boundary explicit; no stateful compatibility method. |
| `contracts/contract.json` | PRESERVE / MODIFY only by owner decision | Keep as the inspected JSON Schema reference, including canonical converter/preparator paths; do not add ADCM evaluator metadata. |
| `contracts/ux_rules.json` | NEW/MODIFY | Keep the requested provider-neutral enrichment DSL as a Forge input/fixture. |
| `examples/contract-rules.json` | PRESERVE | Keep as a legacy/reference rule fixture; document its alias and reachability limitations. |
| `tests/test_contract_schema_rules.py` | MODIFY after explicit artifact-path decision | Point tests at the authoritative/owner-approved fixture and retain negative coverage for missing or stale paths. |
| `docs/DESIGN_DECISIONS.md` | MODIFY | Record ownership, the missing production Forge blocker, and the resolved schema-test path. |
| `docs/architecture/modules/contract-schema.md` | MODIFY | Keep current artifact facts and reachability evidence current. |
| `docs/architecture/system-context.md` | MODIFY | Describe configuration and fixture ownership without claiming ADCM schema authority. |
| `IMPLEMENTATION_PLAN.md` | MODIFY only for verified status/link changes | Keep the master document as an index, not a duplicate contract. |

## Public contracts

- `Settings` remains the application configuration model. Existing keys (`llm_model`, `session_backend`, `audit_backend`, `contract_forge_transport`) remain compatible. Any new source/endpoint key must be optional and descriptive; it selects an adapter and never contains parsed rules.
- `ContractForgePort` exposes only:

  ```python
  async def evaluate_draft(request: ContractInput) -> ContractEvaluationResult: ...
  async def validate_final(request: ContractInput) -> FinalValidationResult: ...
  async def render_yaml(request: RenderRequest) -> RenderedContract: ...
  ```

- A configuration/ownership record, if exposed publicly, must identify the selected transport and opaque source reference. It must not expose conversation history, evidence, superseded candidates, or a Forge session identifier.

## Inputs and outputs

Inputs are repository configuration, JSON artifacts, and the existing typed Forge port. Outputs are:

- a verified artifact/ownership report;
- deterministic configuration validation errors for missing or conflicting source settings;
- the unchanged mock Forge behavior for local tests;
- an explicit `BLOCKED_INPUT` note for the absent production Forge source/transport, while preserving the local UX bundle as a fixture.

The stage does not produce a `ContractEvaluationResult` itself; only a Forge adapter does.

## State ownership

ADCM owns `Settings` and the classification of local fixtures. Forge owns production schema/rule/enrichment state behind its own boundary. No schema cache, rule catalog, or enrichment state may be stored in `ConversationState` or parsed by `src/adcm/application`.

## Data flow

```text
repository artifacts + configuration
        -> baseline/ownership verification
        -> adapter selection (mock/local/remote)
        -> stateless ContractForgePort boundary
        -> later ADCM workflow stages
```

## Required behavior / how it should work

1. Load and validate JSON syntax for `contracts/contract.json`, `contracts/ux_rules.json`, the active `*.contract.json` examples, and `examples/contract-rules.json`.
2. Report that the reachable root of `contracts/contract.json` requires `metadata`, `source`, `targets`, and `orchestration`; the component definitions used by `converter`/`preparator` are reachable, while unrelated imported legacy definitions remain outside the current root graph.
3. Report the 12-rule legacy catalog separately from the 14 annotations currently present in `contract.json`; do not silently treat them as equivalent.
4. Search the repository for enrichment bundles and Forge endpoints. The requested local `contracts/ux_rules.json` exists; no agreed production Forge source/endpoint is present, so retain that blocker in the stage status.
5. Keep configuration failures explicit and early. A remote transport without an endpoint/source is invalid configuration; a missing optional fixture is a test setup error, not an empty rule set.
6. Preserve the logical stateless request/response types so Stage 3 can add a provider without changing ADCM state ownership.

## Forbidden implementation shortcuts

- Bundling a hand-written enrichment fallback into `src/adcm`.
- Treating `examples/contract-rules.json` as executable production policy.
- Silently accepting both snake_case and camelCase aliases without Forge-side compilation/ambiguity checks.
- Removing or weakening the missing-schema test instead of resolving its artifact ownership.
- Adding a hidden global singleton that caches schema or enrichment rules in ADCM.

## Error semantics

- Malformed JSON or an owner-approved schema mismatch is a configuration/fixture error and must identify the file and reason.
- Missing required remote Forge source or transport contract yields `BLOCKED_INPUT` for the stage; the implementer must stop rather than treat the local fixture as production authority.
- Unsupported transport selection is a configuration error.
- Forge transport, validation, and capability errors remain for later stages; this stage must not map them to user workflow statuses.

## Status semantics

Stage readiness uses the roadmap status `READY` or `BLOCKED_INPUT`. It must not introduce Forge or ADCM workflow statuses. Later stages use the canonical enums from `docs/MCP_CONTRACT.md`.

## Schema revision semantics

No revision is generated by this baseline stage. The stateless port must retain the `expected_schema_revision` field so a real Forge can return and validate a revision token in Stage 3.

## Rendering semantics

No new rendering behavior. The mock renderer remains a test adapter; production YAML authority stays with Forge and will be invoked only after stabilization in later stages.

## Template semantics

No template evaluation is added. Forge may later resolve enrichment-time `{source}` placeholders and must preserve runtime `{{env}}`, `{{date:%Y%m%d}}`, and `{{var.name}}` for the Airflow DAG Generator.

## Arrays and paths

This stage records, but does not implement, the distinction between schema wildcard paths (for example `source.columns[*].name`) and concrete instance paths (for example `source.columns[0].name`). ADCM must not flatten the nested schema into a path/value map.

## Value precedence

No candidate resolution occurs here. Forge will report priority/specificity for conflicts among Forge rules; ADCM will apply origin precedence in Stage 1. LLM output cannot choose either precedence.

## Tests

- **Unit/config:** valid and invalid transport/source combinations; no parsed schema state appears in ADCM settings.
- **Artifact contract:** JSON syntax, root shape, reachable-definition report, and explicit count/reachability discrepancy for `x-contract-rules` versus the legacy catalog.
- **Negative:** a stale or missing schema path must fail explicitly; the artifact test uses the owner-approved `contracts/contract.json` and must not recreate the deleted filename.
- **Boundary:** `MockContractForgeAdapter` still satisfies all three `ContractForgePort` operations and rejects an unexpected schema revision.
- **Documentation/tooling:** ownership and blocker facts appear in `docs/DESIGN_DECISIONS.md` and the contract-schema architecture document.

## Acceptance criteria

- `python -m pytest -q tests/test_contract_schema_rules.py` passes against the explicitly approved `contracts/contract.json` artifact; no rule content is silently rewritten.
- A repository search confirms `contracts/ux_rules.json` is present as a local fixture, while Stage 3 remains `BLOCKED_INPUT` until the production Forge source/transport is supplied.
- Configuration can select the mock/reference transport without importing a schema evaluator.
- No file under `src/adcm` parses `contract.json` or `examples/contract-rules.json` as production policy.
- The master plan links to all stage contracts and contains only roadmap-level decisions.

## Explicit non-goals

Production Forge transport, enrichment storage, alias normalization, workflow retries, semantic interpretation, durable persistence, HTTP, UI, and release hardening are deferred to Stages 1–8.

## Documentation updates

Update `docs/DESIGN_DECISIONS.md`, `docs/architecture/modules/contract-schema.md`, `docs/architecture/system-context.md`, and the Stage 3 status in `IMPLEMENTATION_PLAN.md` if the owner supplies or withholds the missing inputs. Do not mark source freshness current solely because a stage contract changed.

## Completion checklist

- [x] Artifact inventory and ownership decision recorded.
- [x] Missing enrichment/Forge inputs explicitly reported: Stage 3 is `BLOCKED_INPUT`.
- [x] Configuration boundary verified without an ADCM schema evaluator.
- [x] Schema-test path decision is explicit and covered by tests.
- [x] No application workflow or transport code added beyond the stated configuration boundary.
- [x] Documentation links and roadmap status reviewed; Stage 0 is formally `READY`.
