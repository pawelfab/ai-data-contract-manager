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
    settings.py
    model_factory.py
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
  test_settings.py
  test_model_factory.py
```

## 2. Current implemented flow

`ADCMOrchestrator`:
- starts a Forge session;
- presents the first pending requirement;
- on each user message tries deterministic extraction against current pending paths;
- if deterministic extraction yields no values, invokes the semantic resolver only
  for the semantic requirements before the next explicit workflow gate;
- never sends an `explicit` requirement to the LLM;
- then runs a bounded stair-step loop to reuse earlier conversation facts for newly exposed pending requirements;
- presents the first remaining requirement or completion/validation state.

`ContractForge`:
- owns canonical session state;
- exposes source-system gate;
- labels requirements as `explicit` or `semantic`, using
  `x-acdm-input-mode` from the schema where applicable;
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

The source-system gate, source-type discriminator and `metadata.id` are explicit
workflow gates. They are handled by deterministic parsing/Pydantic validation and
Forge validation, without LLM extraction. The current `contract.json` does not
define `dataFieldId`; when the contract owner adds it, marking it with
`"x-acdm-input-mode": "explicit"` gives it the same behavior without changing ADCM.

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

CLI/API/runtime now use one `ADCMSettings` object. It loads the project-root `.env`
for local development, while process environment variables retain precedence for
Cloud Run and other deployments. Enabled providers and model names are observable
without exposing `OPENAI_API_KEY`.

The runtime still defaults to `NoopSemanticResolver`. Enable Pydantic AI with:

```text
ADCM_LLM_MODE=pydantic
```

Provider selection is explicit through `ADCM_LLM_PROVIDER` (`auto`, `model`,
`openai_compatible`, or `vertex`). The local OpenAI-compatible gateway uses:

```text
ADCM_LLM_PROVIDER=openai_compatible
ADCM_MODEL=auto
OPENAI_BASE_URL=http://127.0.0.1:3030/v1
OPENAI_API_KEY=local-gateway
```

`model_factory.build_pydantic_ai_model()` constructs an `OpenAIChatModel` with a
gateway compatibility profile. Structured extraction uses JSON object mode rather
than `tool_choice=required`, which the verified gateway rejects. The result is still
validated as `ExtractionResult`, filtered to current Forge requirements, and then
submitted to Forge for canonical validation.

Vertex remains supported through `ADCM_LLM_PROVIDER=vertex`, `ADCM_VERTEX_MODEL`,
`GOOGLE_CLOUD_PROJECT`, and `GOOGLE_CLOUD_LOCATION`.

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

The current suite has 18 passing tests. Coverage now includes settings validation,
`.env` loading, the OpenAI-compatible model factory, and the exact JSON-mode request
shape through a mocked OpenAI HTTP transport. Existing schema tests explicitly read
UTF-8 and pass on Windows.

Selective LLM routing is covered as well: source-system and `metadata.id` gates do
not reach the semantic resolver, a source-type discriminator is explicit, and a
future schema-defined `dataFieldId` can opt out of LLM extraction through schema
metadata.

A live semantic extraction was also verified against
`http://127.0.0.1:3030/v1` with model `auto`; it returned the expected candidate and
the provider client closed cleanly. Real MCP Streamable HTTP remains a separate
end-to-end verification item.

## 8. Immediate recommended work order

1. Fix `source.columns` partial-input UX and add regression tests.
2. Add Schema Explorer/repository duplicate-contract lookup after all schema-defined
   core identifiers have been collected.
3. Run an end-to-end test with real MCP Streamable HTTP and the enabled semantic resolver.
4. Align the Pydantic AI version constraint and `requirements.lock` during the next dependency refresh.
5. Add a schema/rules compatibility gate/version check.
6. Only then expand optional decisions.

## 9. Do not accidentally regress

While fixing the above, preserve:
- source-system-first flow;
- Forge contract ownership;
- candidate-path restrictions;
- system -> generic -> schema-default enrichment order;
- deterministic heuristics before LLM;
- bounded stair-step reuse of historical facts;
- terminal/API separation from contract semantics.

## 10. Last change

```text
Last change: schema-driven selective LLM routing for explicit workflow gates.
Changed files/classes: Requirement.input_mode, SchemaNavigator.input_mode,
  ContractForge source gates, ADCMOrchestrator._semantic_prefix, contract schema and tests.
Behavior now: source system, source type and metadata.id are resolved without LLM;
  schema owners can mark future fields such as dataFieldId with x-acdm-input-mode.
Tests run/result: 18 passed; focused selective-routing tests passed.
Known issues remaining: source.columns partial-input UX; real MCP HTTP end-to-end;
  dataFieldId is not present in the current contract schema; repository duplicate lookup
  is planned; pyproject requires Pydantic AI >=2.32 while the checked lock/venv contain 1.107.1.
Next concrete task: fix partial source.columns facts or add the Schema Explorer lookup
  once the contract owner defines the complete core identifier set.
```
