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
- treats an existing USER value as already resolved when its remembered UserFact is
  identical, while allowing a newer deterministic correction to be submitted once;
- selects deterministic enum/const, boolean, numeric, constrained string,
  URI/date-format and `array<object>` handlers from Requirement schema metadata;
- keeps only the `pipeline`/`id` and owner/team language aliases in an isolated,
  optional specialized resolver because JSON Schema cannot express those labels;
- records deterministically extracted values as latest per-path `UserFact` entries;
- runs a bounded stair-step loop that checks the UserFact store first, then scans
  user messages newest-to-oldest, and submits one USER candidate per step;
- retains incomplete schema-described `array<object>` values as ADCM-only
  `PartialFact` entries, merges later messages by item identity, and asks only for
  required item properties still missing;
- detects no-progress, rejected/repeated candidates and the maximum step limit;
- invokes the semantic resolver only after UserFacts, deterministic history scanning
  and partial structured merging fail, and only for the semantic prefix exposed by
  Forge before the next explicit gate;
- does not invoke the semantic resolver merely to search for unsolicited overrides
  after Forge has no pending requirements;
- accepts an LLM candidate only when its path is currently allowed, confidence meets
  the configured threshold and evidence maps to exactly one sequenced user message;
- does not invoke semantic fallback for Requirement fragments that Forge marks as
  unsupported; these accept only an explicit JSON representation before Forge
  performs authoritative validation;
- stores an accepted semantic candidate as a latest-per-path `UserFact` with
  `extraction_method=LLM`, while still submitting it to Forge as `origin=USER`;
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
- exposes schema-described `overridable` fields whose current value may be replaced
  by USER: lower-origin values and existing scalar USER values for correction,
  excluding explicit workflow gates;
- exposes resolved `items/properties/required` metadata for array-of-object
  requirements without exposing or interpreting a second full schema engine;
- projects the supported Requirement subset (`type`, enum/const, constraints,
  format, examples and bounded object/array shape) and explicitly lists complex
  schema keywords that ADCM must not interpret;
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

The runtime defaults to `NoopSemanticResolver` and constructs the Pydantic AI
resolver when configured. The orchestrator now calls the configured resolver as a
controlled fallback after deterministic resolution fails:

```text
ADCM_LLM_MODE=pydantic
ADCM_LLM_CONFIDENCE_THRESHOLD=0.80
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
than `tool_choice=required`, which the verified gateway rejects. Its prompt contains
only current semantic `pending`/`overridable` requirements, their public schema and
question metadata, existing UserFacts and a bounded recent user-message window. It
does not receive the whole contract. `ExtractionResult` remains structured Pydantic
output; the orchestrator independently enforces allowed paths, confidence and an
unambiguous evidence-to-message-sequence mapping before submission.

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

The two service suites have 80 passing tests in total: 58 ADCM tests and 22 Contract
Forge tests. Coverage includes settings validation,
`.env` loading, the OpenAI-compatible model factory, and the exact JSON-mode request
shape through a mocked OpenAI HTTP transport. Existing schema tests explicitly read
UTF-8 and pass on Windows.

Stage 05 enables the semantic resolver in the orchestrator while keeping explicit
gates deterministic and Forge in control of every canonical write.

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
orchestrator extraction and conversation memory. At that stage semantic resolver
results were deliberately not stored as facts.

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

Stage 05 covers deterministic short-circuiting, semantic extraction of an earlier
message, rejection of paths outside the Forge-exposed semantic set, low-confidence
clarification, evidence-based `message_sequence`, USER override of enrichment and
reuse of a stored LLM UserFact without its raw source message. The mocked provider
test also verifies pending/overridable/UserFact prompt context and the absence of the
whole contract payload.

Stage 06 covers new required string and enum fields whose paths do not occur in ADCM
production code, case-insensitive enum normalization, generic scalar constraints,
URI/date formats, `array<object>` on an unrelated path, dynamic CLI input selection
and a controlled unsupported-`anyOf` flow that neither guesses nor invokes the LLM.
Forge tests verify that new schema fields are discovered, projected and still
validated authoritatively.

Stage 07 adds real-service E2E coverage for the complete A-E matrix: a rich first SAP
message, latest-owner correction before and after the first Forge submit, partial
column merging, deterministic-before-LLM behavior, illegal semantic-path rejection
and a new required schema field. The integration suite launches Contract Forge in its
own virtual environment and talks through MCP Streamable HTTP; separate assertions
exercise the FastAPI and terminal boundaries. A loop-guard regression covers
`max_auto_steps`.

The full Forge suite currently emits one non-fatal third-party
`IncompleteFieldDefinitionWarning` while importing the MCP server.

A live semantic extraction was also verified against
`http://127.0.0.1:3030/v1` with model `auto`; it returned the expected candidate and
the provider client closed cleanly. Real MCP Streamable HTTP was verified between
the two independently installed services, including a complete Rocket contract flow.

## 8. Immediate recommended work order

1. Add Schema Explorer/repository duplicate lookup as a separate MCP integration.
2. Add the explicit schema/rules compatibility gate described by open decision O-003.

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
exposes schema-known editable values through `ForgeState.overridable`. Stage 07 adds
existing scalar USER values to that list for controlled correction while excluding
explicit workflow gates; ADCM skips values already equal to the canonical USER value.

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
values. Stage 05 stores accepted semantic results in the same latest-per-path
UserFact store with `extraction_method=LLM`.

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

## 15. Stage 05 semantic fallback implementation map

- `SemanticResolver` receives separate semantic `pending` and `overridable` lists,
  existing UserFacts and the conversation transcript; it returns `ExtractionResult`
  with typed candidates instead of a path/value dictionary.
- `PydanticAISemanticResolver` sends only a bounded recent user-message window and
  structured requirement/fact context. It keeps no autonomous workflow or provider
  conversation state and receives no full contract snapshot.
- ADCM stops the semantic field list at the next `input_mode=explicit` gate and
  locally rejects unknown paths, confidence below `ADCM_LLM_CONFIDENCE_THRESHOLD`
  and evidence that does not identify exactly one user-message sequence.
- A semantic fact is written to `ConversationMemory` only after Forge accepts the
  USER candidate and canonical state progresses. Debug logs contain method, path and
  confidence, but no values, transcripts or provider payloads.
- UserFacts remain the durable in-memory structured context when an older raw message
  falls outside the resolver prompt window; no summarization service or vector store
  was added.

## 16. Stage 06 schema-driven requirements implementation map

- `HeuristicResolver` no longer receives the contract snapshot. It dispatches from
  `Requirement.value_schema` to enum/const, boolean, integer/number, string pattern,
  URI/date/email format and Stage 04 array/object handlers.
- Enum matching is case-insensitive and permits fuzzy correction only above a high
  threshold with an unambiguous winning choice. Failed enum matching cannot fall
  through to the generic string handler.
- `metadata.id` and `metadata.owner` remain only inside
  `LabeledContractFieldResolver`: they preserve useful `pipeline:`, `owner:` and
  email extraction that standard schema metadata cannot represent. URI extraction
  is no longer path-specific; Forge schemas now expose standard `format: uri`.
- Forge adds `unsupported_schema_keywords` to Requirement for complex constructs in
  the bounded projected fragment. ADCM stops deterministic/semantic inference at
  such a field, asks for explicit JSON and still sends that candidate to Forge for
  validation; it does not implement `anyOf`/`allOf`/conditional semantics.
- `AssistantTurn.pending_requirement` exposes the same Requirement metadata to thin
  clients. The CLI chooses multiline entry from the `array<object>` shape instead of
  checking `source.columns`.

## 17. Stage 07 E2E and cleanup implementation map

- `tests/integration/test_stage07_real_mcp.py` starts Contract Forge as a separate
  process from its own `.venv`; ADCM never imports the Forge package. It covers the
  required scenarios A-E plus real API and CLI smoke tests.
- Mixed rich messages now extract exactly one cron-shaped fragment from history and
  ignore incomplete labelled scalar lines while parsing an `array<object>` block.
- Label-specific `metadata.id`/`metadata.owner` aliases require token boundaries and
  ignore URI contents. `owner jednak team_b` records `team_b`, not the correction word.
- Forge exposes an existing semantic scalar USER field as editable after validation.
  Explicit gates require their dedicated flow, while structured corrections stay on
  the pending/partial protocol because canonical items may contain nested defaults.
  ADCM compares the latest UserFact with `current_value`, so it submits only a changed
  USER candidate.
- Semantic fallback stops when required fields are complete. Deterministic corrections
  remain possible through Forge metadata, and `max_auto_steps`, no-progress and
  repeated-candidate guards remain independent.
- The model audit found one `CandidateValue` and `UserFact` in ADCM and one precedence
  table/write path in Forge. Requirement/Origin DTOs exist once per independently
  deployed service by design; no cross-service Python import was introduced.

## 18. Last change

```text
Last change: completed user-priority/fact-store Stage 07.
Changed files/classes: ADCM mixed-message heuristics, USER correction/no-op handling,
  completed-state semantic guard and max-step regression; Forge editable USER
  Requirement exposure; real-MCP A-E/API/CLI integration tests and test documentation.
  No new ADR was required because D-002, D-004, D-005 and D-012 already define these
  boundaries.
Behavior now: all staged scenarios run through the deterministic ADCM loop and Forge
  validation. Rich first messages, latest-owner correction, partial arrays, bounded
  semantic fallback and new schema fields work without ADCM canonical mutation or an
  LLM-controlled MCP loop.
Tests run/result: ADCM 58 passed and Forge 22 passed through the repository pre-push
  quality gate. Forge
  retains one known, non-fatal IncompleteFieldDefinitionWarning from the MCP
  dependency.
Known issues remaining: dataFieldId is not present in the current contract schema;
  raw semantic transcript context remains a 20-user-message window, while UserFacts
  preserve already extracted values; repository duplicate lookup remains planned.
Next concrete task: Schema Explorer/repository lookup or the schema/rules compatibility
  gate, kept outside the completed staged series.
```
