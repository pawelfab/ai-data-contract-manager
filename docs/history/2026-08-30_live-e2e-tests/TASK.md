---
status: completed
created: 2026-08-30
type: feature
services:
  - ai-data-contract-manager
  - mcp-contract-forge
---

# Task: Live end-to-end tests over the real REST API and the real Contract Forge

## Problem

No test in this repository exercises the real entry point of the system. All 80
existing tests run in-process against hand-written doubles:

- `tests/test_api.py` builds the application through `create_app(...)` and never
  through `composition.build_app()`, so the composition root, environment
  configuration, resolver selection and the MCP adapter are not covered at all;
- every ADCM test replaces Contract Forge with a local `FakeForge` that always
  reports `valid`/`complete`, so real enrichment, real `missing` computation and
  real `valid/complete/clean` signals have never been observed together;
- `ForgeMcpAdapter` has a single test that substitutes the MCP client;
- `PydanticAIIntentResolver` has no coverage whatsoever.

The consequence is that the path `HTTP -> composition root -> MCP -> Forge ->
stabilization -> document` is unverified. In particular the two behaviors that
carry the most business risk — recomputation of derived values after a source
system change, and the authority of an explicit user value over an application
rule — are only proven against a Forge that cannot disagree.

`docs/NEXT_ITERATIONS.md` item 9 and the "Intentionally not implemented yet"
section of `docs/CURRENT_STATE.md` both record the absence of end-to-end coverage
for the SC/EC matrix.

## Goal

A black-box test suite that talks to a really running ADCM, which really calls a
really running Contract Forge, exclusively over the public REST contract.

Observable outcome: for each covered scenario the suite asserts on the final
`document`, on `missing`, on `valid`/`complete`/`clean`, on the changes produced
by successive turns, on the absence of stale values, and on the behavior of
`MUTATION` / `KNOWLEDGE` / `MIXED` / `UNRESOLVED`.

Scenarios that depend on a real LLM are marked separately and are non-blocking.

## Scope

Included:
- a `live` suite under `ai-data-contract-manager/tests/live/` that starts Contract
  Forge and ADCM as subprocesses on ephemeral ports and drives them over HTTP;
- ADCM started through `uvicorn --factory adcm.adapters.api.composition:build_app`,
  so the real composition root is under test;
- `live` and `llm` pytest markers plus a default `addopts` selector that keeps both
  out of the existing test run;
- deterministic scenarios (`ADCM_INTENT_MODE=heuristic`):
  S1 source system to enrichment, S2 source system change with recompute and stale
  retraction, S3 explicit user value over application rule, S4 knowledge query
  without mutation, S6 unresolved without mutation, S7 complete followed by a later
  field edit, S8 foreign field leading to `clean` plus an explicit message;
- LLM scenarios (`ADCM_INTENT_MODE=pydantic-ai`), non-blocking:
  S5 mixed intent, S4' knowledge query, S6' unresolved;
- an opt-in `system_test` quality command, deliberately outside `pre_push`;
- documentation of how to run both selections.

## Out of scope

- any change under `src/` in either service;
- any change to `mcp-servers/mcp-contract-forge/resources/contract.json` or to
  `ai-data-contract-manager/resources/ux_rules.json`;
- any change to the 80 existing tests;
- scenarios that the baseline contract fixture cannot express: SC-03, SC-05,
  SC-10, SC-11, SC-07, SC-08, SC-09;
- asserting the *content* of an answer to a knowledge query (not implemented, see
  Constraints);
- adding a `MIXED` branch to the heuristic resolver;
- persistent session storage, authentication, CI wiring.

## Constraints

- Tests must not `import adcm.*` or `import contract_forge.*`. Although the suite
  lives inside the ADCM tree, it communicates with the running services only over
  HTTP, and locates the repository through `pathlib`, not through a production
  import.
- Assertions use only the public REST contract: `document`, `contract_status`,
  `missing`, `diagnostics`, `unresolved`, `changes`, `message`. No
  `ADCM_DEBUG_API`, no provenance, no mutation log. Per `docs/CORE_INVARIANTS.md`
  #18 the domain models are not the public contract.
- Docker is not available on the development machine, so orchestration is by
  subprocess, not by `docker compose`.
- Both service virtual environments must remain separate; neither service's venv
  may be used to run the other service.
- `MIXED` cannot be produced by `HeuristicIntentResolver`, which emits only
  `MUTATION`, `KNOWLEDGE` and `UNRESOLVED`. S5 therefore exists only as an `llm`
  test.
- `EffectiveIntentResolution.knowledge_query` is computed but never consumed:
  it is absent from `TurnOutcome`, and `BasicResponseComposer` returns the same
  status text for a `KNOWLEDGE` turn as for a mutation turn. A knowledge scenario
  can therefore assert only that the document did not change. The business
  criterion behind SC-13 is not implementable today.
- Expected values are pinned from one real run of the stack, never guessed. A
  divergence between the real run and the expected enrichment chain is reported as
  a result, not absorbed by weakening an assertion.
- Per `AGENTS.md` #17, a failing scenario is first classified (defect, missing
  configuration, adapter problem, missing abstraction, wrong boundary) before any
  code changes.

Constraints control expected scope, but they are not proof that an input, contract, schema or assumption is correct. If preserving a constraint requires disproportionate workaround complexity, record and escalate it in `IMPLEMENTATION.md`.

## Acceptance criteria

- [x] The suite starts Contract Forge and ADCM as subprocesses on ephemeral ports,
      waits for both `/health` endpoints, and terminates both on teardown with no
      orphaned listeners and no writes into the repository `logs/` directories.
- [x] ADCM under test is built by `composition.build_app()` via `uvicorn --factory`.
- [x] S1: after `"system sap"` the document carries the derived values, status is
      `valid=true, complete=false, clean=true`, and `missing` is exactly
      `/metadata/dataFileId`.
- [x] S2: after `"system rocket"` no key or string value anywhere in the document
      contains `sap`, the sap-derived paths are absent, and `changes` contains
      remove operations.
- [x] S3: an explicit `/metadata/id` value survives a later, unrelated turn, the
      derived `/converter/outputFilename` follows it, and the last user decision wins.
- [x] S4: a knowledge query leaves `document`, `missing` and `contract_status`
      identical, returns no `changes` and no `unresolved`, and still increments `turn_no`.
- [x] S6: an unrecognizable message returns the clarification message, a non-blank
      `unresolved` reason, no changes, and neither `YAML:` nor `valid=` in the message.
- [x] S7: the contract reaches `complete` with a YAML artifact, survives a later
      edit of the same field as a `replace` carrying the previous `old_value`, and
      returns to `complete=false` when that value is removed.
- [x] S8: a field that is foreign for the active shape is absent from the document
      and its removal is stated explicitly in the message.
- [x] `pytest ai-data-contract-manager/tests -q` collects and passes exactly the
      same tests as before this task; the new markers do not filter any of them out.
      (74 collected and passed before and after; the 19 deselected are the new tests.)
- [x] `-m live` runs without touching an LLM; `-m llm` skips rather than fails when
      the LLM endpoint is unavailable, and is excluded from the default selector.
- [x] Deliberately weakening one rule in `ux_rules.json` makes S1 and S2 fail
      (assertion strength is proven, not assumed). Six live tests failed with precise
      diffs; the rule was restored.

- [x] `scripts/agent/quality_gate.py --profile pre-push` exits 0. This initially failed
      for a pre-existing reason unrelated to this task — the Contract Forge suite could
      not resolve `resources/contract.json` when invoked from the repository root,
      reproduced on unmodified `HEAD`. Reported first, then fixed on explicit maintainer
      instruction by pinning `FORGE_CONTRACT_PATH` in the gate command.
      See `IMPLEMENTATION.md` -> Unexpected findings.

## Relevant references

- issue/ticket: `docs/NEXT_ITERATIONS.md` item 9 — "Dodać testy E2E dla całej
  macierzy SC/EC z dokumentu biznesowego"
- prior task/decision: `docs/history/2026-08-30_unresolved-intent-contract/`,
  `docs/history/2026-08-30_intent-resolution-policy/`,
  `docs/history/2026-08-29_rest-api-v1/`
- documentation: `docs/BUSINESS_BEHAVIOR.md` (SC-02, SC-04, SC-06, SC-12, SC-13,
  SC-15, SC-18, SC-19, SC-20, EC-06, EC-07, EC-14, D-01, D-02, J-02, J-04),
  `docs/CORE_INVARIANTS.md`, `docs/ARCHITECTURE_BASELINE.md`,
  `docs/MODULE_CONTRACTS.md`, `docs/CURRENT_STATE.md`
