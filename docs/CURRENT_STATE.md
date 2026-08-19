# ADCM — current state snapshot

**Snapshot date:** 2026-08-19

This file is intentionally operational. Update it after meaningful implementation changes. Before acting on it, compare it with the actual repo.

## 1. Current minimal implementation

The latest minimal package built in this project is `adcm-minimal 0.1.0` and contains roughly this structure:

```text
src/
  adcm/
    orchestrator.py
    heuristics.py
    semantic.py
    gateway.py
    api.py
    cli.py
    runtime.py
    models.py
  contract_forge/
    engine.py
    schema.py
    rules.py
    models.py
    path_utils.py
    mcp_server.py
config/
  contract.json
  ux_rules_original.json
  ux_rules_contract_v1.json
tests/
  test_forge_flow.py
  test_orchestrator.py
  test_schema_dynamic.py
  test_heuristics.py
  test_api.py
```

## 2. Current implemented flow

`ADCMOrchestrator`:
- starts a Forge session;
- presents the first pending requirement;
- on each user message tries deterministic extraction against current pending paths;
- if deterministic extraction yields no values, invokes the semantic resolver;
- then runs a bounded stair-step loop to reuse earlier conversation facts for newly exposed pending requirements;
- presents the first remaining requirement or completion/validation state.

`ContractForge`:
- owns canonical session state;
- exposes source-system gate;
- accepts only currently allowed/pending paths;
- applies system enrichment, generic enrichment, then schema defaults to a fixpoint;
- discovers missing requirements from schema;
- validates local candidate values and the final contract.

## 3. Verified behavior from the first run

The CLI currently starts as intended:

```text
ADCM: Jaki jest system źródłowy? Dostępne: rocket, sap.
```

For SAP it then asks for pipeline id, owner, CSV URI and source columns.

Source system typo matching is implemented; identifiers are normalized (e.g. uppercase user input for `metadata.id` can be canonicalized to schema-safe lowercase form).

## 4. Known bug/UX problem — `source.columns`

Observed input:

```text
data_d, sap1,sap2,sap3
```

and later:

```text
data_d
sap1
sap2
sap3
```

causes the same question to repeat.

### Cause

The current heuristic parser for `source.columns` expects a complete column representation that includes a datatype (or valid JSON). A line with only a column name is rejected. No partial column facts are retained. Forge therefore still reports `source.columns` as missing, and the orchestrator renders the same question again.

### Desired fix

Do not simply accept incomplete columns into the canonical contract. Instead:
1. parse and retain partial names in ADCM conversation memory;
2. determine what subfields are missing (typically `dataType`);
3. ask a narrower clarification;
4. once complete, submit a valid `source.columns` candidate to Forge.

Add tests for comma-separated names, newline-separated names and mixed `name TYPE` inputs.

## 5. LLM configuration today

The current runtime defaults to a no-op semantic resolver unless:

```text
ADCM_LLM_MODE=pydantic
```

is set.

Current intended Vertex-related environment variables include:

```text
ADCM_VERTEX_MODEL
GOOGLE_CLOUD_PROJECT
GOOGLE_CLOUD_LOCATION
```

The package contains an `.env.example`, but the application does **not currently load `.env` automatically**. Environment variables need to be set externally unless configuration loading is added.

### Desired configuration improvement

Create one explicit settings/configuration object (for example Pydantic Settings) used by CLI/API/runtime, with:
- `.env` support for local development;
- environment variables in Cloud Run;
- startup logging of selected modes/model names without logging secrets;
- validation of incompatible/missing settings.

Do not hide whether the LLM is enabled. The CLI/API should make the active semantic mode observable.

## 6. Current rules/schema issue

The original enrichment rules target an older contract layout (`bronzeTable`, `silver.tables`, `gold.entries`, parts of `converter.source`, `rawData`). The current `contract.json` uses `targets.bronze/silver/gold` and a different converter/source layout.

The minimal package therefore keeps:
- original rules unchanged for reference;
- a smaller migrated rules file for the current schema.

Important known inconsistencies:
- `@daily` does not satisfy the current five-field cron regex;
- a fixed-width rule references a `length` semantic inconsistent with the half-open range model/current properties;
- some custom `x-contract-rules` are not sufficiently machine-readable to execute generically.

## 7. Current tests

The last package reported 11 passing tests for the in-process path, covering the core Forge/ADCM behaviors and dynamic schema discovery.

**Important:** real MCP Streamable HTTP was implemented but was not verified in the original sandbox because optional MCP/Pydantic AI dependencies could not be installed there. Verify it in the actual development environment before treating it as proven.

## 8. Immediate recommended work order

1. Fix `source.columns` partial-input UX and add regression tests.
2. Introduce explicit settings with `.env` support and observable LLM mode.
3. Run an end-to-end test with real MCP Streamable HTTP and enabled Pydantic AI/Vertex.
4. Add a schema/rules compatibility gate/version check.
5. Only then expand optional decisions and/or Schema Explorer integration.

## 9. Do not accidentally regress

While fixing the above, preserve:
- source-system-first flow;
- Forge contract ownership;
- candidate-path restrictions;
- system -> generic -> schema-default enrichment order;
- deterministic heuristics before LLM;
- bounded stair-step reuse of historical facts;
- terminal/API separation from contract semantics.

## 10. Update section after next change

When code changes, replace this section with:

```text
Last change:
Changed files/classes:
Behavior now:
Tests run/result:
Known issues remaining:
Next concrete task:
```
