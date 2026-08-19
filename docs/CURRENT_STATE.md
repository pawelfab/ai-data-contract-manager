# ADCM — current state snapshot

**Snapshot date:** 2026-08-19

This file is intentionally operational. Update it after meaningful implementation changes. Before acting on it, compare it with the actual repo.

## 1. Current minimal implementation

The repository is now a monorepo containing two independently installable services:

```text
docs/                                      # cross-service documentation
ai-data-contract-manager/
  src/adcm/
  tests/
  docs/
  scripts/
  pyproject.toml
  requirements.lock
  .venv/
mcp-servers/mcp-contract-forge/
  src/contract_forge/
  config/
  contracts/
  tests/
  docs/
  pyproject.toml
  requirements.lock
  .venv/
```

There is no root `pyproject.toml`. ADCM and Forge have separate dependency graphs,
entry points and virtual environments.

## 2. Current implemented flow

`ADCMOrchestrator`:
- starts a Forge session through MCP Streamable HTTP;
- presents the first pending requirement;
- assigns a monotonic sequence to every user message while preserving the full
  transcript;
- on each user message tries deterministic extraction against current `pending` and
  Forge-exposed `overridable` paths;
- records deterministically extracted values as latest per-path `UserFact` entries;
- runs a bounded stair-step loop that checks the UserFact store first, then scans
  user messages newest-to-oldest, and submits one USER candidate per step;
- detects no-progress, rejected/repeated candidates and the maximum step limit;
- deliberately does not invoke the semantic resolver in Stage 03;
- presents the first remaining requirement or completion/validation state.

ADCM has no import-time or packaging dependency on `contract_forge`. Its local
`ForgeState`, `Requirement` and related models validate the JSON wire response. Unit
tests use a fake `ForgeGateway`, not an in-process Forge engine.

`ContractForge`:
- owns canonical session state;
- exposes source-system gate;
- labels requirements as `explicit` or `semantic`, using the workflow policy from
  `ux_rules_contract_v1.json`;
- accepts only currently allowed/pending paths;
- applies system enrichment, generic enrichment, then schema defaults to a fixpoint;
- applies every canonical value through one origin-precedence write function;
- exposes schema-described `overridable` fields whose current origin is system
  enrichment, generic enrichment or schema default;
- accepts a valid USER override for an existing schema-known USER/enrichment/default
  value and reports rejected candidates separately from final contract validation;
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
Forge validation, without LLM extraction. `contract.json` remains read-only input
and contains no ADCM workflow annotations. The current contract does not define
`dataFieldId`; its future path is already classified as `explicit` in the UX rules,
so it will receive the same behavior when the contract owner adds the field.

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

CLI/API/runtime now use one `ADCMSettings` object. It loads the ADCM service-root `.env`
for local development, while process environment variables retain precedence for
Cloud Run and other deployments. Enabled providers and model names are observable
without exposing `OPENAI_API_KEY`.

The runtime still defaults to `NoopSemanticResolver` and can construct the Pydantic
AI resolver when configured. Stage 03 deliberately does not invoke either resolver;
the configuration below remains available for resolver tests and the later controlled
semantic-fallback stage:

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
gateway compatibility profile. The resolver component uses JSON object mode rather
than `tool_choice=required`, which the verified gateway rejects. Its result is
validated as `ExtractionResult` and filtered to Forge-exposed requirements, but the
orchestrator does not consume it until the planned semantic-fallback stage.

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

The two service suites have 42 passing tests in total: 24 ADCM tests and 18 Contract
Forge tests. Coverage includes settings validation,
`.env` loading, the OpenAI-compatible model factory, and the exact JSON-mode request
shape through a mocked OpenAI HTTP transport. Existing schema tests explicitly read
UTF-8 and pass on Windows.

Stage 03 keeps the semantic resolver disabled in the orchestrator. Resolver/model
factory tests remain in place for the later semantic-fallback stage, while current
orchestrator tests assert that no LLM call occurs.

The Stage 00 baseline regression explicitly protects the source-system-first gate,
the next requirement exposed by Forge, two automatic history-driven submissions,
and the state ownership boundary. ADCM `ConversationMemory` owns the transcript and
does not contain a contract; Forge owns canonical `SessionData.contract`, does not
contain conversation messages, and returns contract snapshots that cannot mutate its
canonical state.

Stage 01 adds focused coverage for USER overrides of system enrichment, lower-origin
rejection, SYSTEM versus GENERIC, GENERIC versus SCHEMA_DEFAULT, USER-to-USER
correction, invalid override preservation/diagnostics, and rejection of unknown
schema paths. The ADCM regression also verifies that semantic extraction is submitted
as `origin=USER`.

Stage 02 covers latest-user-fact replacement, rejection of an older fact, equal
sequence replacement, fact extraction metadata/evidence, monotonic user-message
sequence with a preserved transcript, and integration between deterministic
orchestrator extraction and conversation memory. Semantic resolver results are
deliberately not stored as facts yet.

Stage 03 covers facts supplied before Forge reveals their requirements, latest USER
fact selection, USER override of a system-enriched schedule, a single precise question
when no fact exists, and termination with diagnostics when a candidate makes no
progress. Forge coverage verifies schema-derived override metadata and removal of an
override candidate after its origin becomes USER.

The full Forge suite currently emits one non-fatal third-party
`IncompleteFieldDefinitionWarning` while importing the MCP server.

A live semantic extraction was also verified against
`http://127.0.0.1:3030/v1` with model `auto`; it returned the expected candidate and
the provider client closed cleanly. Real MCP Streamable HTTP was verified between
the two independently installed services, including a complete Rocket contract flow.

## 8. Immediate recommended work order

1. Fix the `source.columns` partial-input UX in Stage 04.
2. Add the controlled LLM fallback only in its planned later stage.
3. After the staged series, add Schema Explorer/repository lookup and a schema/rules
   compatibility gate.

## 9. Do not accidentally regress

While fixing the above, preserve:
- source-system-first flow;
- Forge contract ownership;
- candidate-path restrictions;
- system -> generic -> schema-default enrichment order;
- deterministic heuristics before LLM;
- bounded stair-step reuse of historical facts;
- terminal/API separation from contract semantics.

## 10. Stage 00 baseline implementation map

The stage documents use shorthand paths such as `src/adcm/orchestrator.py` and
`src/contract_forge/engine.py`. In the current monorepo the actual paths are under
the independent service roots:

- `ai-data-contract-manager/src/adcm/orchestrator.py` owns the deterministic
  conversation and stair-step loop;
- `ai-data-contract-manager/src/adcm/models.py` owns `ConversationMemory` and the
  client-side Forge response DTOs;
- `ai-data-contract-manager/src/adcm/heuristics.py` and `semantic.py` resolve only
  currently exposed requirements;
- `mcp-servers/mcp-contract-forge/src/contract_forge/engine.py` owns canonical
  sessions, candidate submission, enrichment/default progression and state output;
- `mcp-servers/mcp-contract-forge/src/contract_forge/schema.py` owns schema-based
  requirement discovery and validation;
- the regression tests are in each service's `tests/test_orchestrator.py` and
  `tests/test_forge_flow.py`.

No production behavior changed in Stage 00. Known product limitations remain the
partial `source.columns` UX, the absent `metadata.dataFieldId` in the current schema,
and the planned repository duplicate lookup.

## 11. Stage 01 precedence implementation map

Forge now uses one business-origin order:

```text
USER > SYSTEM_ENRICHMENT > GENERIC_ENRICHMENT > SCHEMA_DEFAULT > STRUCTURAL
```

- `contract_forge.models.can_replace()` is the single precedence decision;
- `contract_forge.path_utils.write_value()` is the single canonical value/origin/
  `AppliedValue` writer and supports paths through existing array items;
- `RuleEngine`, source-type enrichment and `SchemaNavigator` defaults/structural
  containers use that writer;
- `ContractForge.submit_values()` still accepts pending paths and additionally permits
  USER replacement only for an existing schema-known value whose current origin is
  USER, SYSTEM_ENRICHMENT, GENERIC_ENRICHMENT or SCHEMA_DEFAULT;
- invalid or disallowed submissions leave the canonical value intact and appear in
  `ForgeState.candidate_issues`; they do not make a valid canonical contract invalid;
- ADCM submits facts extracted deterministically or semantically as `origin=USER`.

Forge does not compare user message sequence. ADCM owns the UserFact store and Forge
exposes lower-origin values through `ForgeState.overridable` for the Stage 03 loop.

## 12. Stage 02 user-fact memory implementation map

ADCM conversation memory now owns USER message recency:

- `ChatMessage.message_sequence` is populated for session user messages only;
- `ConversationMemory.next_message_sequence` assigns monotonic values starting at 1;
- `UserFact` stores path, value, message sequence, extraction method, confidence and
  optional evidence;
- `ConversationMemory.facts[path]` contains only the latest remembered fact;
- `remember_fact()` replaces an entry only for an equal or newer sequence, while
  `get_fact()` performs direct lookup;
- deterministic extraction from the current message and existing historical scan
  records facts with `extraction_method=DETERMINISTIC` and raw-message evidence.

Stage 03 now reads these facts in the stair-step loop and consumes Forge `overridable`
fields. Semantic results are still not stored because the LLM is disabled in this
stage. Partial columns and persistence remain later work.

## 13. Stage 03 stair-step resolution implementation map

- Contract Forge derives `overridable` fields from canonical provenance plus the
  active schema; no orchestrator path allowlist is used.
- Every exposed override includes its current value, current origin, public value
  schema, allowed values and question/description.
- ADCM evaluates `pending` before `overridable`, checks UserFacts before history,
  scans history newest-to-oldest and submits exactly one USER candidate per step.
- Candidate diagnostics are propagated to `AssistantTurn`; unchanged state, a
  repeated candidate and `max_auto_steps` stop automatic progression.
- Exact numeric cron extraction is conservative because the contract's five-token
  regex alone also matches ordinary five-word sentences.
- LLM fallback, generic array/object parsing and partial structured facts remain out
  of scope for this stage.

## 14. Last change

```text
Last change: completed user-priority/fact-store Stage 03.
Changed files/classes: Forge/ADCM Requirement and ForgeState DTOs, schema-derived
  override discovery, deterministic ADCM stair-step orchestration, candidate issue
  presentation, cron extraction guard, focused T1-T5 tests and MCP smoke scenario.
Behavior now: Forge exposes legal lower-origin override candidates; ADCM reuses the
  latest deterministic UserFacts and prior messages to submit one USER value at a
  time until it needs genuinely missing information. The LLM remains disabled.
Tests run/result: ADCM 24 passed and Forge 18 passed. The real Streamable HTTP smoke
  completed a Rocket contract and applied a schedule stated before source selection.
  Forge retains one known, non-fatal IncompleteFieldDefinitionWarning from the MCP
  dependency.
Known issues remaining: source.columns partial-input UX; dataFieldId is not present
  in the current contract schema; semantic fallback and repository duplicate lookup
  remain planned.
Next concrete task: Stage 04 from docs/user_priority_and_fact_store, implemented
  separately without pulling in later LLM behavior.
```
