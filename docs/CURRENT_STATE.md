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
- retains incomplete schema-described `array<object>` values as ADCM-only
  `PartialFact` entries, merges later messages by item identity, and asks only for
  required item properties still missing;
- detects no-progress, rejected/repeated candidates and the maximum step limit;
- deliberately does not invoke the semantic resolver through Stage 04;
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
- exposes resolved `items/properties/required` metadata for array-of-object
  requirements without exposing or interpreting a second full schema engine;
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

## 4. Resolved UX problem — partial `array<object>` input

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

is now retained as four partial items instead of being discarded.

ADCM derives the item shape from the Forge requirement schema, records a
conversation-scoped `PartialFact`, and returns a narrower clarification listing the
missing fields and affected item names. A later `name TYPE` response is merged by
the schema-derived identity field. Only a complete candidate is submitted to Forge.

The parser supports JSON arrays of objects, multiline `name TYPE`, comma/newline
name lists, case-insensitive enum matching, and fixed-width name/start/end/type
records. It is activated by the schema shape rather than the `source.columns` path.

## 5. LLM configuration today

CLI/API/runtime now use one `ADCMSettings` object. It loads the ADCM service-root `.env`
for local development, while process environment variables retain precedence for
Cloud Run and other deployments. Enabled providers and model names are observable
without exposing `OPENAI_API_KEY`.

The runtime still defaults to `NoopSemanticResolver` and can construct the Pydantic
AI resolver when configured. Stage 04 deliberately does not invoke either resolver;
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

The two service suites have 51 passing tests in total: 32 ADCM tests and 19 Contract
Forge tests. Coverage includes settings validation,
`.env` loading, the OpenAI-compatible model factory, and the exact JSON-mode request
shape through a mocked OpenAI HTTP transport. Existing schema tests explicitly read
UTF-8 and pass on Windows.

Through Stage 04 the semantic resolver remains disabled in the orchestrator. Resolver/model
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

Stage 04 covers comma- and newline-separated partial names, later merging of types,
complete `name TYPE` input, JSON arrays, invalid datatype clarification, fixed-width
items, and a different test path to prevent `source.columns` hardcoding. A regression
also prevents one pasted source structure from overriding a schema-compatible
derived target array.

The full Forge suite currently emits one non-fatal third-party
`IncompleteFieldDefinitionWarning` while importing the MCP server.

A live semantic extraction was also verified against
`http://127.0.0.1:3030/v1` with model `auto`; it returned the expected candidate and
the provider client closed cleanly. Real MCP Streamable HTTP was verified between
the two independently installed services, including a complete Rocket contract flow.

## 8. Immediate recommended work order

1. Add the controlled LLM fallback only in its planned later stage.
2. Continue the schema-driven requirements work from the staged plan.
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

Stage 03 reads these facts in the stair-step loop and consumes Forge `overridable`
fields. Stage 04 adds a separate `partial_facts` store for incomplete structured
values. Semantic results are still not stored because the LLM remains disabled;
persistence remains later work.

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
- LLM fallback remained out of scope for this stage; generic partial array/object
  parsing is implemented separately in Stage 04.

## 14. Stage 04 partial structured input implementation map

- Forge resolves chained local `$ref` values and exposes only the minimal public
  item structure required for deterministic `array<object>` parsing.
- ADCM stores incomplete structures as `PartialFact` values outside the canonical
  contract and never converts them to `UserFact` until all required item fields exist.
- Follow-up records merge by a schema-derived string identity property, normally
  `name`; enum values normalize case-insensitively without datatype alias guessing.
- Narrow clarification messages list missing fields, affected records, invalid
  values, the expected record layout and schema enum choices.
- To avoid ambiguous meaning, a complex pasted structure binds only to Forge's first
  current requirement (or an already-started partial), while scalar Stage 03
  overrides continue to use the full exposed field set.

## 15. Last change

```text
Last change: completed user-priority/fact-store Stage 04.
Changed files/classes: Forge public schema projection and chained-ref handling;
  ADCM PartialFact memory, generic structured parser/merger, partial clarification,
  focused T1-T5/regression tests, D-013 and the real MCP smoke scenario.
Behavior now: incomplete array/object input remains only in ADCM memory, receives a
  precise missing-data question, and reaches Forge only after deterministic merging
  produces a complete candidate. The LLM remains disabled.
Tests run/result: ADCM 32 passed and Forge 19 passed. The real Streamable HTTP smoke
  retained a fixed-width names-only partial, merged ranges/types, completed the
  Rocket contract and preserved the derived target columns as generic enrichment.
  Forge retains one known, non-fatal IncompleteFieldDefinitionWarning from the MCP
  dependency.
Known issues remaining: dataFieldId is not present in the current contract schema;
  semantic fallback and repository duplicate lookup remain planned.
Next concrete task: the next stage from docs/user_priority_and_fact_store, without
  pulling in later unrelated behavior.
```
