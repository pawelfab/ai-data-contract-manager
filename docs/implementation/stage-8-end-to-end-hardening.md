# Stage 8 — Real-contract end-to-end hardening and release gates

## Goal

The complete ADCM flow is proven against the owner-approved Contract Forge schema/enrichment package and representative end-to-end scenarios. Domain invariants, fast-forward statuses, deferred capabilities, revisions, rendering/cache behavior, runtime templates, persistence/idempotency, API/UI reads, and documentation/quality gates are all exercised together. Release is blocked when the authoritative enrichment bundle, Forge source/protocol, or schema-test artifact decision is missing.

## Why this stage exists

Unit and mock workflow tests can prove orchestration order but cannot prove that real canonical paths, aliases, rule scopes, defaults, registry dependencies, and enrichment fallbacks agree. The repository now contains the requested local `contracts/ux_rules.json` fixture, but still lacks an agreed production Forge source/transport and its former test path referenced deleted `contracts/data-contract.schema.json`. These remaining external decisions are release blockers, not invitations to invent fixtures. This stage is the final evidence pass once the external owner supplies the missing inputs.

## Preconditions

- Stages 0–7 are complete and their individual acceptance criteria pass.
- Stage 3 has an owner-approved versioned `contract.json`/Forge source, enrichment bundle/repository, alias policy, rule-priority policy, and transport conformance fixtures.
- Stage 5 durable backend and Stage 6 API idempotency are available in CI/test configuration.
- Stage 7 read-only artifact/UI behavior is available for smoke tests.
- If any authoritative input is absent or the schema-test path remains unresolved, mark this stage `BLOCKED_INPUT` and report the exact missing evidence.

## Scope

- Add a real-contract integration fixture set and end-to-end tests that drive `ChatService`/HTTP through Forge and capability adapters.
- Verify every mandatory behavior listed in the generator prompt, with one owning test and an explicit failure diagnosis.
- Exercise canonical path compilation/alias ambiguity, enrichment/default/user precedence, Forge rule priority/scope, default-triggered requirements, unknown-system generic fallback, and runtime DSL preservation.
- Exercise ADCM evidence/provenance, deterministic corrections, arrays/path projection, CurrentSchemaView replacement, capability deferral/retry/blocking, status mapping, schema revision mismatch, and render cache behavior.
- Run configured quality, architecture-documentation, and freshness checks; preserve known unrelated failures as blockers rather than weakening tests.
- Produce release notes/checklist with test evidence and any external dependency still unresolved.

## Out of scope / Do not do

- Do not treat the local UX fixture as production authority or reconstruct additional enrichment rules from `examples/contract-rules.json`, examples, or prose.
- Do not add production schema/rule evaluation to ADCM to make integration tests pass.
- Do not introduce a database-migration root, deployment manifest, event bus, graph framework, or multi-agent runtime.
- Do not relax invariants, statuses, revision checks, or render gating for a green build.
- Do not claim full release readiness when tests use only the mock Forge or stale/deleted schema paths.

## Architectural boundaries

- **ADCM:** state, provenance, resolution, orchestration, capability routing, API/read models, persistence, and presentation.
- **Contract Forge:** authoritative schema/enrichment/rule/validation/YAML behavior under test.
- **LLM:** semantic tests use provider mocks/fakes and production adapter contract; no path or precedence authority.
- **Other MCPs:** capability handlers are deterministic test doubles or approved integrations; they never mutate drafts.
- **Airflow DAG Generator:** downstream consumer of runtime DSL; tests assert Forge preserves DSL, not that ADCM translates it.

## Invariants

All global invariants must have an owning test in this stage's matrix or a referenced earlier test:

- no unauthorized draft path; no direct LLM/MCP mutation;
- selected `ResolvedValue` always points to an evidenced/origin-bearing candidate;
- user Evidence and SignalBinder provenance are strict;
- preferences may fan out only over legal current paths;
- history is superseded, not deleted;
- deterministic tie-breaking never uses UUID ordering;
- current schema view replaces old branches;
- nested arrays and instance paths are preserved;
- Forge is stateless and ADCM owns workflow state;
- schema revision is separate from draft hash;
- rendering occurs once after stabilization and FINAL is hash/revision/validation gated;
- runtime DSL is preserved for the Airflow DAG Generator.

## Files affected

| File | Action | Purpose |
|---|---|---|
| `tests/integration/` | NEW | Owner-approved real Forge/schema/enrichment end-to-end fixtures and tests. |
| `tests/test_contract_schema_rules.py` | MODIFY | Use the explicitly approved schema artifact and retain rule reachability/alias regression checks. |
| `tests/test_candidate_resolver.py` | MODIFY if integration reveals contract gaps | Keep precedence/scope/correction assertions aligned with real Forge metadata. |
| `tests/test_workflow.py` | MODIFY | Add cross-boundary capability/revision/render scenarios. |
| `tests/test_api.py` | MODIFY | Add durable idempotency and stable-response smoke tests. |
| `tests/test_api_read_only.py` | MODIFY | Add artifact/read-model smoke coverage. |
| `tests/test_e2e_contract.py` | NEW | Full user-turn-to-rendered-artifact scenarios. |
| `docs/TESTING_STRATEGY.md` | MODIFY | Record the final integration matrix and required gates. |
| `docs/ISSUES_AND_RESOLUTIONS.md` | MODIFY | Record any real-contract discrepancies and approved resolutions. |
| `docs/DESIGN_DECISIONS.md` | MODIFY | Record release evidence and remaining decisions. |
| `IMPLEMENTATION_PLAN.md` | MODIFY | Mark stage statuses and link final evidence without duplicating details. |
| `docs/architecture/system-context.md` | MODIFY only where current behavior changed | Synchronize system-level release evidence. |
| `docs/architecture/modules/application.md` | MODIFY only where current behavior changed | Synchronize application responsibilities. |
| `docs/architecture/modules/adapters.md` | MODIFY only where current behavior changed | Synchronize transport/persistence/UI adapter facts. |
| `docs/architecture/modules/contract-schema.md` | MODIFY only where current behavior changed | Synchronize owner-approved schema/enrichment evidence. |
| `docs/architecture/flows/turn-lifecycle.md` | MODIFY only where current behavior changed | Synchronize end-to-end ordering and stable outcomes. |
| `docs/architecture/flows/contract-forge-workflow.md` | MODIFY only where current behavior changed | Synchronize Forge/revision/render evidence. |
| `docs/architecture/symbols/application.md` | MODIFY only where current behavior changed | Synchronize public application symbols. |
| `docs/architecture/symbols/adapters.md` | MODIFY only where current behavior changed | Synchronize adapter symbols and failures. |
| `pyproject.toml` | VERIFY / MODIFY only by explicit owner decision | Keep the configured pytest/quality gates authoritative; do not add deployment settings. |

## Public contracts

No new application API is introduced. The stage validates the public contracts from Stages 1–7:

- stateless Forge operations and canonical statuses;
- `WorkflowOutcomeStatus` values;
- `ContractPath`/nested draft and `CurrentSchemaView` authorization;
- versioned sessions/idempotent audit and `POST /sessions/{session_id}/messages`;
- read-only session/draft/artifact models and DRAFT/FINAL render modes.

Integration fixtures must use the exact owner-approved wire/schema versions and must not introduce test-only public statuses or path aliases.

## Inputs and outputs

Inputs are real contract/enrichment artifacts, deterministic capability results, sanitized user scenarios, and provider transport fixtures. Outputs are test evidence, release-gate results, artifact/hash/revision receipts, and explicit blocker reports. No integration test may silently replace a missing input with an empty rule set or generic fixture.

## State ownership

Tests construct and inspect ADCM `ConversationState` through public services. Forge integration receives only `ContractInput` snapshots and returns typed results. Test harnesses may reset isolated stores between cases but must not bypass persistence/version/idempotency contracts in end-to-end scenarios.

## Data flow

```text
sanitized user turn + session
  -> semantic adapter/fake
  -> Evidence/signals/preferences/revisions
  -> ADCM fast-forward + real Forge + capability doubles
  -> stable outcome + final validation
  -> durable save/audit
  -> one keyed Forge render
  -> API/read model/UI artifact assertion
```

## Required behavior / how it should work

1. Load the owner-approved schema and enrichment bundle through Forge's production boundary; assert that ADCM does not parse them.
2. Compile canonical paths and aliases. Unknown or ambiguous aliases fail deterministically; legacy snake_case rule paths are not guessed against camelCase schema properties.
3. Verify candidate precedence: user explicit > user preference/existing/external values > Forge enrichment/derived/default according to the canonical origin map; Forge internal rule priority/specificity is explicit and scope stays on candidates.
4. Verify a default such as `preparator.enabled=true` can activate a new required operation and that the workflow asks the user or resolves a capability instead of falsifying the default.
5. Verify unknown system-specific enrichment uses the approved generic fallback and does not crash generic onboarding.
6. Verify a correction such as CSV → Parquet replaces `CurrentSchemaView`, removes delimiter/fixed-width paths from the current nested draft, and preserves superseded evidence/candidates.
7. Verify arrays and concrete `ContractPath` indices, including `{}` padding for skipped object-list positions.
8. Verify user-origin Evidence is required and SignalBinder propagates the same evidence IDs/source signal ID without fabrication; selected candidate scope is inspected on the candidate.
9. Verify a single user turn fast-forwards through empty-requirement candidate stages, deferred capability retry, and final external blocking/`BLOCKED_EXTERNAL` when unresolved.
10. Verify semantic parser tests remain separate from WorkflowRunner tests; use deterministic typed fakes in end-to-end workflow cases where NLP is not under test.
11. Verify schema revision mismatch is surfaced, `draft_hash` excludes revision, and artifact cache key is `(draft_hash, schema_revision, render_mode)`.
12. Verify `render_yaml` is called once after stabilization for a changed key, DRAFT/FINAL modes are exact, and FINAL requires a same-hash/same-revision VALID receipt.
13. Verify runtime `{{env}}`, `{{date:%Y%m%d}}`, and `{{var.name}}` survive Forge rendering unchanged while enrichment-time `{source}` is resolved by Forge.
14. Run full tests and repository documentation/freshness commands; record failures with their owning path and do not weaken assertions.

## Forbidden implementation shortcuts

- Replacing the real Forge with `MockContractForgeAdapter` while calling the test “end-to-end”.
- Deleting tests for the missing schema path or adding a generated copy that is not owner-approved.
- Using UUID ordering, candidate list order, or UI edits to mask nondeterminism.
- Invoking Forge/render multiple times in a way hidden by a mock call counter.
- Treating a successful HTTP 200 as release proof when persistence/audit/idempotency was bypassed.
- Marking stale architecture documentation current without updating impacted curated files.

## Error semantics

- Missing/invalid owner artifacts or Forge endpoint: `BLOCKED_INPUT` release status with exact evidence request; local `contracts/ux_rules.json` does not remove this blocker.
- Alias/rule/schema conformance failure: integration failure identifying canonical path/rule ID and provider version.
- Capability unavailable/final deferred: stable `BLOCKED_EXTERNAL`, not a false `COMPLETE`.
- User requirement unresolved: `WAITING_FOR_USER` with exact legal paths.
- Schema revision mismatch: explicit conflict/change failure; no stale artifact is accepted.
- Persistence/idempotency conflict: explicit 409/application failure; no duplicate turn.
- Any unexpected exception: `FAILED`/test failure with diagnostic; never swallowed for a green build.

## Status semantics

The integration matrix must assert the exact canonical values:

```text
evaluate_draft: INCOMPLETE | COMPLETE | INVALID
finding:        VALID | INVALID | DEFERRED
validate_final: VALID | INVALID | DEFERRED_EXTERNAL
workflow:       WAITING_FOR_USER | BLOCKED_EXTERNAL | COMPLETE | INVALID | FAILED
```

No provider or UI-specific alias is accepted in public responses.

## Schema revision semantics

Every real Forge response is tagged with a revision. Tests send it back on subsequent calls, induce a mismatch, and assert explicit failure. `draft_hash` covers canonical nested draft content only; artifact identity adds revision and mode separately.

## Rendering semantics

Render is a separate post-stabilization operation. DRAFT and FINAL are the only modes; FINAL is blocked without matching VALID final validation. Integration tests instrument the Forge adapter to assert one call per changed cache key and zero calls for unchanged keys.

## Template semantics

The integration suite includes both enrichment-time `{source}` resolution and runtime DSL preservation. No ADCM or Forge test may translate runtime DSL into Airflow/Jinja; that behavior belongs to the downstream DAG Generator.

## Arrays and paths

Real canonical wildcard paths and concrete instance paths are tested together. The suite verifies that path authorization is evaluated against the current view and that nested list/object serialization survives persistence, API read models, and YAML rendering.

## Value precedence

The matrix includes same-path candidates from user, preference, Forge enrichment, derived, and defaults, plus multiple Forge rules with explicit priority/specificity/scope. Expected winners are specified independently of candidate UUID/list order and selected candidate metadata is traceable to Evidence/source IDs.

## Tests

The following tests are mandatory owners for the prompt's required coverage:

| Test area | Protects |
|---|---|
| Forge alias/path compilation | canonical normalization and ambiguity failure |
| enrichment/default/user precedence | ADCM origin ranking and Forge candidates |
| rule priority/scope | Forge internal priority; scope remains on candidate |
| default activates required rule | reevaluation after candidate application |
| unknown system fallback | generic onboarding resilience |
| CurrentSchemaView correction | replacement, reprojection, preserved history |
| deterministic corrections | revision/sequence, no UUID ordering |
| arrays/ContractPath | nested draft and wildcard/instance semantics |
| Evidence/SignalBinder | strict user evidence and provenance propagation |
| fast-forward/capability | empty requirements, deferred retry, final external block |
| semantic parser separation | workflow independence from NLP |
| schema revision/render | mismatch, hash separation, one stabilized render/cache |
| runtime DSL | Forge preserves Airflow-facing templates |
| persistence/API/UI | durable versioning, idempotency, stable read-only artifacts |

## Acceptance criteria

- All mandatory test areas have passing, owner-approved fixtures and a named test path.
- The full configured test command passes in the selected environment, or every failure is an explicit unresolved blocker with no weakened test.
- Real Forge integration proves stateless calls, canonical statuses, alias/rule/enrichment behavior, revision consistency, and template/render semantics.
- End-to-end API retry proves no duplicate semantic/Forge/capability/render/audit side effects.
- Architecture docs and freshness checks are synchronized for any changed application behavior; no deployment/migration artifact is invented.
- Release status is `READY` only when the external inputs and all gates are present.

## Explicit non-goals

Production deployment, authentication/authorization, editable YAML, Airflow DAG generation, and new infrastructure are outside the repository's current scope and require separate decisions.

## Documentation updates

Update `docs/TESTING_STRATEGY.md`, `docs/ISSUES_AND_RESOLUTIONS.md`, `docs/DESIGN_DECISIONS.md`, impacted curated architecture documents, and `IMPLEMENTATION_PLAN.md` status. Run the documented `repo_inventory.py`, `doc_impact.py`, `doc_freshness.py --mark-current`, and `doc_freshness.py --check` procedures only after the final code/docs diff is verified.

## Completion checklist

- [ ] Authoritative schema, enrichment bundle, endpoint/protocol, and revision policy are present.
- [ ] Mandatory real-contract/integration matrix passes.
- [ ] All global invariants have an owning passing test.
- [ ] End-to-end persistence, idempotency, API, read model, and render behavior passes.
- [ ] Full quality/documentation/freshness gates pass or blockers are recorded.
- [ ] No test shortcut, schema evaluator, migration root, or deployment manifest was introduced.
