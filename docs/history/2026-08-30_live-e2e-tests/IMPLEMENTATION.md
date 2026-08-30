---
status: completed
created: 2026-08-30
completed: 2026-08-30
---

# Implementation: Live end-to-end tests over the real REST API and the real Contract Forge

## Implementation contract

Owning service: `ai-data-contract-manager` (test layer only).

Owning boundary: the test suite. This task adds **no production code**. It exercises
the existing public REST contract of ADCM and the existing MCP contract between ADCM
and Contract Forge. If a scenario cannot pass without touching `src/`, that is a
finding to record below, not a change to make silently.

Files expected to change:
- `ai-data-contract-manager/pyproject.toml` — `markers`, `addopts`
- `ai-data-contract-manager/requirements-dev.txt` — declare `httpx2` explicitly
- `ai-data-contract-manager/tests/live/conftest.py` (new)
- `ai-data-contract-manager/tests/live/helpers.py` (new)
- `ai-data-contract-manager/tests/live/test_live_enrichment.py` (new)
- `ai-data-contract-manager/tests/live/test_live_authority.py` (new)
- `ai-data-contract-manager/tests/live/test_live_intent_kinds.py` (new)
- `ai-data-contract-manager/tests/live/test_live_completeness.py` (new)
- `ai-data-contract-manager/tests/live/test_live_llm_intent.py` (new)
- `scripts/agent/config.json` — new `quality_commands.system_test`
- `README.md` — "Testy live" section
- `docs/CURRENT_STATE.md` — test inventory and the not-yet-implemented list

Files/services explicitly not to change:
- `ai-data-contract-manager/src/**` and `mcp-servers/mcp-contract-forge/src/**`
- `mcp-servers/mcp-contract-forge/resources/contract.json`
- `ai-data-contract-manager/resources/ux_rules.json`
- the 12 existing ADCM test files and the 3 existing Forge test files
- `scripts/agent/config.json` -> `pre_push_quality_stages` (the new stage stays opt-in)
- the empty repository-root `tests/` directory

Main invariant: **the tests talk to the system exclusively through the public HTTP
contract.** No `import adcm.*`, no `import contract_forge.*`, no `ADCM_DEBUG_API`,
no provenance and no mutation log. A test that needs internal state to make its point
is a test that is asserting the wrong thing.

Implementation approach: session-scoped pytest fixtures launch Contract Forge and
ADCM with `subprocess.Popen` on ephemeral ports, gate on both `/health` endpoints,
and tear both down. ADCM is started through
`uvicorn --factory adcm.adapters.api.composition:build_app`, so the composition root
— untested until now — is the thing under test. Scenarios are expressed as sequences
of `POST /v1/sessions/{id}/turns` calls with assertions on the response body only.

Tests:
- deterministic (`live`, `ADCM_INTENT_MODE=heuristic`): S1, S2, S3, S4, S6, S7, S8
- non-blocking (`llm`, `ADCM_INTENT_MODE=pydantic-ai`): S5, S4', S6'
- regression guard: the existing 80 tests must collect and pass unchanged

Architecture risks:
- **Marker misconfiguration silently shrinking the existing run.** Adding
  `addopts = -m "not live and not llm"` to a shared `pyproject.toml` affects every
  existing invocation. Mitigation: compare collected test counts before and after.
- **Process leakage on Windows.** Mitigated by running uvicorn without `--reload`
  (single process, so `terminate()` is sufficient) and by asserting no orphaned
  listeners after the run.
- **Assertions coupled to a Polish message string.** S8 can only observe foreign
  removal through `message`, because `foreign` is not part of the public contract.
  Accepted deliberately; recorded as a known fragility.
- **Suite rot.** The `live` suite is opt-in, so nothing forces it to run. Mitigated
  by documenting it in `README.md` as a required step before closing a task; this is
  a process control, not a technical one, and it is the weakest point of the design.

## Current behavior

See `docs/CURRENT_STATE.md` for the implemented baseline and
`ai-data-contract-manager/README.md` for the REST v1 contract. Relevant to this task:

- `tests/test_api.py` covers the public API shape using `create_app(...)` with
  `FakeForge` and `FakeIntent`; `composition.build_app()` is never invoked by a test.
- `tests/test_stabilization.py` and `tests/test_proposals.py` already prove the rules
  and reconciliation logic — user override and stale retraction — but against a
  `FakeForge`, so Forge defaults, enrichment and `missing` never participate.
- `mcp-servers/mcp-contract-forge/tests/test_analyzer.py` already proves the analyzer
  against the real `resources/contract.json`, but in-process, without MCP.
- Nothing joins the two halves. There is no test in which a rule proposal and a Forge
  enrichment proposal are reconciled in the same round against real analysis output.
- There are no `conftest.py` files, no custom markers and no CI in the repository.

## Planned changes

1. **Task documentation** — this directory, created before implementation begins.
2. **Marker and dependency setup** — add `markers` and
   `addopts = -m "not live and not llm"` to `ai-data-contract-manager/pyproject.toml`;
   declare `httpx2` in `requirements-dev.txt` (today it is only a transitive
   dependency of `mcp`). Verify the existing suite collects the same test count.
3. **Fixtures** — `tests/live/conftest.py` with `free_port()`, a service-process
   context manager that captures stdout/stderr and surfaces them on a health-gate
   timeout, `forge_service`, `adcm_heuristic`, and a lazily started `adcm_llm`;
   `tests/live/helpers.py` with the HTTP client wrapper and the assertion helpers
   `flatten_pointers`, `assert_document_unchanged`, `assert_no_stale_value`,
   `assert_status`. A missing service venv produces a clear skip.
4. **Pin expected values** — one real run of the stack; record the actual turn
   responses as the reference for the scenario assertions.
5. **Scenarios** — S1/S2 in `test_live_enrichment.py`, S3 in `test_live_authority.py`,
   S4/S6 in `test_live_intent_kinds.py`, S7/S8 in `test_live_completeness.py`,
   S5/S4'/S6' in `test_live_llm_intent.py`.
6. **Wiring and documentation** — `system_test` command in `scripts/agent/config.json`
   outside `pre_push_quality_stages`; `README.md` section; `docs/CURRENT_STATE.md`
   update; then the completion procedure below.

Prefer the smallest local change that satisfies the task while preserving the boundaries recorded in `docs/ARCHITECTURE_BASELINE.md` and `docs/CORE_INVARIANTS.md`.

## Unexpected findings

### Finding: the configured quality gate cannot run the Contract Forge suite

Observation: `python scripts/agent/quality_gate.py --profile pre-push` fails with
`FileNotFoundError: 'resources\contract.json'` in
`mcp-servers/mcp-contract-forge/tests/test_observability.py::test_correlation_id_is_technical_metadata_only`.
The same suite passes (12/12) when pytest is invoked with the Forge directory as the
working directory. Verified against a clean `git stash` of this task's changes: the
failure is present on unmodified `HEAD` and is **not** caused by this task.

Affected assumption: the task assumed `--profile pre-push` was a usable green baseline
against which to prove "no regression".

Implementation impact: none on the delivered suite. The regression criterion was met by
running each service suite in its own directory, exactly as the root `README.md`
documents ("Weryfikacja bez Docker"): ADCM 74 passed, Forge 12 passed.

Root cause: `contract_forge.server` resolves `FORGE_CONTRACT_PATH` (default
`resources/contract.json`) relative to the process working directory, while
`quality_commands.test` invokes pytest from the repository root.

Workaround complexity: none needed for this task.

Simpler corrective option: either run the Forge command with the service directory as
cwd, or set `FORGE_CONTRACT_PATH` to a repository-relative path in that command, or make
the test set the variable itself. One line either way.

Decision: **reported first, then fixed on the maintainer's explicit instruction.**
`scripts/agent/` is a protected path, so the defect was surfaced rather than silently
patched; the maintainer then asked for the path-resolution fix. The Forge command in
`quality_commands.test` now pins the contract path explicitly:

```
set "FORGE_CONTRACT_PATH=mcp-servers\mcp-contract-forge\resources\contract.json" && ...
```

This makes contract resolution independent of the working directory instead of relying
on the gate happening to be invoked from the right place. `logs/` is gitignored and the
log directory already resolved to the repository root under the previous command, so the
fix changes nothing else. `--profile pre-push` is now green: 74 + 12 passed, exit 0.

### Finding: expected limitations confirmed by the first real run

Observation: all three limitations anticipated during planning were confirmed once the
real stack ran.

- `MIXED` is produced by the LLM resolver (the `llm` scenario passes) and is
  unreachable through `HeuristicIntentResolver`, which has no such branch.
- A `KNOWLEDGE` turn returns `'valid=True, complete=False, clean=True\nbrak: ...'` —
  the same text as a mutation turn. `knowledge_query` never reaches the user.
- The baseline fixture has no `gold`/`preparator`/`rawData`/`bronzeTable`, no
  oneOf/discriminator and no variant-specific fields.

Affected assumption: that the business acceptance criterion behind SC-13 is testable.
It is not; only the "no mutation" half is.

Implementation impact: S5 exists only as an `llm` test; S4/S4' assert absence of
mutation rather than answer content; SC-03, SC-05, SC-07, SC-08, SC-09, SC-10 and SC-11
are out of reach.

Workaround complexity: making SC-13 testable would require carrying `knowledge_query`
into `TurnOutcome` and teaching the composer to answer — a production change to the
response layer, not a test change.

Simpler corrective option: none within a test-only task.

Decision: recorded as product gaps in `docs/CURRENT_STATE.md` ("Pokrycie live E2E")
rather than worked around. No production code was touched.

### Complexity escalation rule

Unexpected complexity is a signal to re-check assumptions before adding code.

If a simple requirement begins to require substantial workaround logic, many special cases, non-obvious transformations or changes across unrelated components, stop before implementing that complexity and record the finding here.

Do not silently compensate for a likely defect in an input, contract, schema, configuration or protected file.

Applied to this task: if a scenario fails, the first action is to classify the cause
(defect in ADCM, defect in Forge, missing configuration, wrong expectation in the
test). Weakening an assertion, adding a rule to `ux_rules.json`, or extending
`contract.json` to make a test green are all forbidden responses.

## Deviations from the original plan

The plan added `test_zz_pin.py`, a throwaway file that dumped real turn responses so the
expected values could be pinned from observation rather than guessed. It was deleted once
the values were transferred into the scenario tests; it is not part of the delivery.

Three scenarios were added beyond the planned set, because the real run made them cheap
and they close obvious holes:
- `test_switching_system_back_restores_the_previous_conventions` (EC-07, returning to a
  previously used system must be deterministic);
- `test_user_value_is_not_resurrected_by_the_rule_after_removal` (removing a user value
  must hand the field back to the rule rather than freeze it forever);
- `test_unresolved_turn_does_not_block_the_next_real_change` (an unresolved turn is an
  episode, not a session state).

## Verification

- [x] relevant unit tests pass — ADCM 74 passed, Forge 12 passed (each in its own venv
      and working directory, per root `README.md`)
- [x] relevant integration tests pass — live suite 15 passed
- [x] architecture/boundary tests pass when applicable — `test_api_architecture.py` and
      both `test_logging_architecture.py` included in the runs above
- [x] configured quality gates pass — `--profile pre-push` exits 0 (74 + 12 passed)
      after the Forge contract-path fix described under Unexpected findings
- [x] documentation freshness reviewed — `doc_freshness.py --check` reports `CURRENT`
- [x] `docs/generated/documentation-impact.md` reviewed — it lists
      `ai-data-contract-manager/README.md` and `docs/CURRENT_STATE.md`; both updated
- [x] required curated documentation updated

Task-specific verification:

- [x] existing ADCM suite collects 74 before and after the new `addopts` (19 deselected
      are exactly the 15 `live` + 4 `llm` new tests) — no test was filtered out
- [x] `... -m pytest ai-data-contract-manager\tests\live -q -m live` — 15 passed in ~10 s
- [x] `python scripts/agent/quality_gate.py --stage system_test` — 15 passed
- [x] no orphaned listeners after the run; `git status` shows no writes into either
      service's `logs/`
- [x] with `OPENAI_BASE_URL=http://localhost:3030/v1` and `ADCM_MODEL=openai-chat:auto`,
      `-m llm` — 4 passed in ~28 s, including the MIXED scenario
- [x] without those variables, `-m llm` — 4 skipped, 0 failed; `-m live` never contacts
      an LLM (separate fixture, separate ADCM process)
- [x] negative control: changing `sap.source_type` from `csv` to `json` in
      `ux_rules.json` made 6 live tests fail with precise diffs; the rule was restored
      and `git diff` on that file is empty

## Final result

A 19-test black-box suite under `ai-data-contract-manager/tests/live/` that drives a
really running ADCM against a really running Contract Forge over HTTP only.

Delivered: 15 deterministic `live` tests (S1 enrichment chain, S2 source-system change
with stale retraction, S3 user authority over app rules, S4 knowledge query, S6
unresolved, S7 completeness and later edits, S8 foreign field) and 4 non-blocking `llm`
tests (S5 mixed intent, knowledge, value-suggesting question, ambiguous message).

Both markers are excluded from the default selector, so the existing 74-test ADCM run is
untouched. `system_test` is registered as an opt-in quality stage and deliberately kept
out of `pre_push_quality_stages`.

**No production code was changed.** `src/` in both services, `contract.json` and
`ux_rules.json` are byte-identical to `HEAD`.

One out-of-scope repair was made on explicit maintainer instruction after being
reported: the Forge command in `quality_commands.test` now pins `FORGE_CONTRACT_PATH`,
so `--profile pre-push` passes instead of failing on a working-directory assumption.

The suite immediately proved its worth on the first run: it confirmed the full
user → app-rule → Forge-enrichment → Forge-default chain reconciling correctly in one
turn, and it confirmed that switching `sap` → `rocket` leaves no trace of `sap` anywhere
in the document — neither of which any existing test could observe, because they all run
against a `FakeForge` that always reports valid and complete.

## Unresolved items

- The root `README.md` still documents the Forge suite as
  `mcp-servers/mcp-contract-forge/.venv/Scripts/python.exe -m pytest mcp-servers/mcp-contract-forge/tests -q`
  run from the repository root, which fails for the same working-directory reason the
  quality gate did. The gate is fixed; that README line is not. Either it should gain the
  same `FORGE_CONTRACT_PATH` pin, or `contract_forge.server` should resolve its default
  contract path relative to the package rather than the process cwd — the latter is the
  real fix and belongs to the Forge service, not to a test task.
- Whether the `live` suite should eventually become blocking on pre-push. Opt-in for
  now, with a documented obligation to run it before closing a task. Measured runtime is
  ~10 s, so the cost argument for keeping it out is weak; revisit.
- S8 asserts foreign removal through the Polish `message` string, because `foreign` is
  not part of the public REST contract. Changing the composer's wording will break it.
  Accepted per D-02, which makes that message a promise to the user.
- Out of scope, observed while planning, to be raised separately: `pyproject.toml`
  declares `[project.scripts] adcm = "adcm.main:main"` while `adcm/main.py` does not
  exist; `examples/demo_flow.py` imports the non-existent
  `adcm.runtime.build_orchestrator`; `pyproject.toml` pins `uvicorn==0.35.0` while
  `requirements.txt` pins `0.52.4`.

## Completion procedure

Before declaring this task complete:

1. run relevant tests and repository quality gates;
2. verify documentation freshness;
3. review `docs/generated/documentation-impact.md`;
4. update only curated documents whose responsibility or documented behavior changed;
5. record the final implementation result, deviations and unresolved items above;
6. change this document metadata to:

```yaml
status: completed
completed: YYYY-MM-DD
```

7. update `TASK.md` status to `completed`;
8. move the entire task directory from:

`docs/active-task/2026-08-30_live-e2e-tests/`

to:

`docs/history/2026-08-30_live-e2e-tests/`

Do not leave completed task documentation in `docs/active-task/`.
