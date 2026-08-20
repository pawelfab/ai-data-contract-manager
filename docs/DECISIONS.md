# ADCM — architectural decisions

This is a lightweight ADR log. Add a new entry only for a durable decision, not every implementation detail.

---

## D-001 — Contract Forge is the contract owner

**Status:** Accepted

**Decision:** Canonical contract state, enrichment, missing-field discovery and validation belong to Contract Forge MCP. ADCM only submits candidate values and presents results.

**Why:** Prevents business/schema logic from being duplicated in conversational code and keeps ADCM resilient to contract changes.

**Consequence:** ADCM cannot silently patch arbitrary contract paths.

---

## D-002 — ADCM controls the loop; LLM does not

**Status:** Accepted

**Decision:** The orchestration loop is deterministic application code. The LLM is a semantic resolver invoked inside controlled steps.

**Why:** Free-form tool use made the flow harder to reason about and risked bypassing contract ownership.

**Consequence:** LLM output must be constrained to currently permitted paths or another explicit partial-fact protocol.

---

## D-003 — Source system is the first workflow gate

**Status:** Accepted

**Decision:** Every new contract conversation starts by selecting the source system, before generic contract questions.

**Why:** System selection unlocks source type and system-specific enrichment and avoids asking questions that enrichment can answer.

**Consequence:** This is currently a workflow rule even if `metadata.sourceSystemGcpId` is not formally required by JSON Schema. Long term it should be represented explicitly in the contract/rules metadata.

---

## D-004 — Enrichment/default order

**Status:** Accepted

**Decision:** Forge applies, in order: system enrichment -> generic enrichment -> JSON Schema defaults -> missing required discovery.

**Value precedence:** user > system enrichment > generic enrichment > schema default.

**Consequence:** Lower-priority mechanisms must not overwrite stronger values silently.
Deterministic and LLM extraction are methods of obtaining a USER fact, not separate
business origins. Recency between USER facts belongs to ADCM; Forge accepts a later
valid USER submit without comparing message sequence.

---

## D-005 — Heuristics before LLM

**Status:** Accepted

**Decision:** Use deterministic normalization/parsing first; use an LLM only where semantics/history add value.

**Why:** Lower cost, lower latency, predictable behavior, easier tests.

**Consequence:** Heuristics need explicit tests for common input formats and must support partial extraction where useful.

---

## D-006 — Dynamic schema within explicit boundaries

**Status:** Accepted

**Decision:** Forge should dynamically react to ordinary `contract.json` changes supported by the schema navigator, but new executable rule semantics require a registered implementation.

**Why:** Full interpretation of arbitrary custom rule prose is unsafe and non-deterministic.

**Consequence:** Schema/rules compatibility needs explicit diagnostics/versioning.

---

## D-007 — ADCM does not guess legacy path migrations

**Status:** Accepted

**Decision:** When rules and `contract.json` use incompatible structures, do not infer mappings such as `bronzeTable` -> `targets.bronze` at runtime in ADCM.

**Why:** Cardinality and semantics may have changed, especially for Silver/Gold.

**Consequence:** Migrations belong to the rule/schema owner and should be explicit/versioned.

---

## D-008 — UI is thin

**Status:** Accepted

**Decision:** Terminal is the initial UI. Future web UI calls the same API/orchestrator and does not own schema/rule logic.

**Consequence:** Specialized widgets may improve data entry, but their values still go through ADCM/Forge validation.

---

## D-009 — Schema Explorer is a separate MCP

**Status:** Accepted / planned

**Decision:** Environment/repository lookups belong to Schema Explorer MCP; contract semantics stay in Contract Forge. ADCM coordinates both.

**Examples:** BigQuery table existence, naming rules, schema lookup, repository YAML discovery.

**Consequence:** Avoid direct MCP-to-MCP coupling unless later justified.

---

## D-010 — Favor a working vertical slice over premature framework expansion

**Status:** Accepted

**Decision:** For the demo, support a small number of systems and a complete conversation/validation path before implementing a highly generic multi-stage framework.

**Why:** A previous dynamic/staged redesign grew substantially without producing a stable demo.

**Consequence:** Generalization is done after observed behavior stabilizes, without violating D-001..D-009.

---

## D-011 — Contract requirements select explicit or semantic input

**Status:** Accepted

**Decision:** Forge exposes an input mode for each requirement. The workflow section
of `ux_rules_contract_v1.json` maps contract paths to `explicit` when they must be
answered through deterministic parsing/Pydantic and Forge validation without LLM
extraction. All other requirements default to `semantic`. `contract.json` is never
modified to carry ADCM workflow policy.

**Why:** Source selection and core identifiers determine later branches and future
repository lookups. They must remain predictable, auditable and explicitly confirmed.

**Consequence:** ADCM may invoke the LLM only for the semantic prefix before the next
explicit gate; it never sends an explicit requirement to the semantic resolver.
The current source-system gate, source-type discriminator and `metadata.id` are
explicit. The UX rules already classify the future `metadata.dataFieldId`; ADCM does
not create that field while it is absent from `contract.json`.

---

## D-012 — ADCM and every MCP are independent services in one monorepo

**Status:** Accepted

**Decision:** The monorepo root owns cross-service documentation and tooling. ADCM
lives under `ai-data-contract-manager/`; Contract Forge lives under
`mcp-servers/mcp-contract-forge/`. Each service owns its source tree, tests,
documentation, manifest, lock snapshot and virtual environment.

**Why:** Deployment and dependency boundaries must match the runtime architecture.
The former in-process adapter let ADCM import Forge implementation types and obscured
whether the MCP transport really worked.

**Consequence:** ADCM no longer supports `--local-forge` and never imports the
`contract_forge` package. It validates MCP responses with client-side DTOs and uses
a fake gateway in unit tests. Contract schema, rules and contract artifacts belong
only to the Forge service. A minimal local run requires both service processes.

---

## D-013 — Incomplete structured facts stay outside the canonical contract

**Status:** Accepted

**Decision:** ADCM stores incomplete `array<object>` values as conversation-scoped
`PartialFact` entries. It submits a value to Contract Forge only after every
schema-required item property has been supplied deterministically.

**Why:** Useful user input must survive clarification, but an invalid draft must not
enter the canonical contract or weaken Forge validation.

**Consequence:** Forge exposes a minimal resolved public schema fragment
(`items.type`, `items.properties`, `items.required`) so ADCM can identify missing
data. Forge remains the sole validator of the merged complete candidate. Partial
facts are currently in-memory and disappear with the ADCM session.

---

## D-014 — Unknown source systems use the generic Forge path

**Status:** Accepted

**Decision:** The first source-system Requirement exposes configured systems as
hints, not as a closed enum. Forge accepts another schema-valid identifier. If it is
not configured in the enrichment rules, Forge does not run source-type selection or
system-specific enrichment for it; Forge asks for `source.sourceType` and then runs
generic enrichment, JSON Schema defaults and ordinary requirement discovery.

**Why:** A new source system must be usable before a dedicated enrichment profile is
added, without baking the currently known systems or business fallback rules into
ADCM.

**Consequence:** Custom-system conversations usually contain more questions and
receive no values with `SYSTEM_ENRICHMENT` origin. ADCM keeps fuzzy matching for the
configured hints, but it does not impose an additional custom-system naming pattern
when the supplied schema provides none; the user must enter the intended identifier.
In that unconstrained case deterministic extraction requires a direct single-token
answer so earlier conversational facts are not consumed as the source selection;
this restriction is not written to or treated as validation of the canonical schema.
Configured-system membership and all canonical validation remain owned by Forge.
D-003 and the precedence/order from D-004 remain unchanged.

---

## D-015 — A contract Forge cannot execute is a configuration error, not an invalid session

**Status:** Accepted

**Decision:** Contract definitions are compiled before any session exists. Loading walks
every `x-contract-rules` entry in the document — including `$defs` no property references
yet — and rejects unknown kinds, unknown operators, unparseable rules and duplicate rule
ids with a `ContractDefinitionError`. Rules whose logic is not expressed structurally (no
`assertion`, e.g. `registry_lookup`) are reported as `skipped_non_executable`: they never
create a requirement, never set `invalid`, and never block completion. `kind` names only
the consequence of a violation; the logic lives in `condition`/`assertion` and is never
inferred from `message`, `notes` or the originating Pydantic validator.

**Why:** Mixing the two failure worlds made an unsupported contract look like a user
mistake. A user could answer fifteen questions before learning that Forge cannot execute
the contract at all, and a single unsupported rule could make completion unreachable
forever. Prose-parsing would also violate the ownership rule in `AGENTS.md`.

**Consequence:** The service refuses to start on a contract it cannot execute, which is
deliberate. Adding a new rule kind or operator is a Forge code change with a
deterministic handler and a test — see
`mcp-servers/mcp-contract-forge/docs/CONTRACT_RULES.md`. Rule paths are relative to the
schema node carrying the rule; a cross-section rule would need a DSL extension, not a
code workaround.

---

## D-016 — Requirements carry an operational `status`; `reason` is open metadata

**Status:** Accepted

**Decision:** `Requirement` gains `status` (`missing` / `invalid` / `forbidden`), which is
what ADCM branches on, plus `rule_id` and `message`. `reason` stays as descriptive
provenance and its type is relaxed from a `Literal` to a plain `str`. ADCM keeps its own
structurally mirrored DTOs and never imports Forge models:
Forge internal models → Forge transport DTO → MCP/JSON → ADCM transport DTO → ADCM domain.

**Why:** `reason` mixed two questions ("why does this exist" and "what is wrong"). Pinning
it to a `Literal` on both sides also meant every new discovery reason in Forge was a
breaking change at the transport boundary.

**Consequence:** ADCM resolves only `missing` requirements automatically; `invalid` and
`forbidden` are phrased as correction requests. `reason="invalid"` is still accepted for
compatibility and is expected to be replaced gradually by a real cause
(`schema_validation`, `pattern`, `contract_rule`).

---

## D-017 — `complete` is a contract state, not the end of the session

**Status:** Accepted

**Decision:** A completed contract stays editable. Forge exposes a third, separate
surface next to `pending` and `overridable`:

- `pending` — what is missing,
- `overridable` — derived values worth confirming against user facts,
- `editable` — everything in the active contract the user may deliberately change,
  regardless of provenance.

`editable` is served by its own MCP tool, `get_editable_fields(session_id)`, rather than
riding along in every `ForgeState`, so the ordinary stair-step loop does not carry the
whole catalogue. A user may write any path the active schema resolves, including paths
that do not exist yet; validation, `x-contract-rules` and origin precedence still apply.
Arrays are one atomic edit unit — `source.columns`, never `source.columns.0.name` — and
ADCM turns "add a column" into a replacement of the whole array. No JSON Patch.

**Why:** Ending the conversation at `complete` made the last answer irreversible. Mixing
`editable` into `overridable` was rejected because `overridable`'s filters exist to stop
stale conversational facts from silently rewriting explicit or structured user values.

**Consequence:** ADCM resolves an edit from a new user message deterministically first
and only falls back to the LLM when the heuristics cannot place it — the LLM does not run
merely because the contract is complete. A change can reopen the contract, e.g. enabling
`preparator` makes an `x-contract-rule` demand an operation.

---

## D-018 — Changing an input invalidates what Forge derived from it

**Status:** Accepted

**Decision:** Enrichment stays fill-only, but a USER write now invalidates the derived
values that depend on it, so `_advance` recalculates them. Dependencies are read from the
rules' own `source_path`/`fallback_source_path`, so no contract field is hardcoded.
Changing a recompute trigger — today only `metadata.sourceSystemGcpId` — goes further: it
drops every value with an enrichment/default origin, re-runs enrichment for the new
context, and then prunes values that no longer belong to the active schema variant. USER
values are kept throughout; what was actually lost is reported in `ForgeState.discarded`.

**Why:** Provenance makes this cheap, and it is one of the main reasons for having it.
Without it, adding a source column left the target table stale and switching source
systems left a contract mixing `sap_bronze` with Rocket enrichment.

**Consequence:** Forge holds only the current valid contract; the history of what the user
said stays in ADCM's `UserFact` memory, so a value pruned as belonging to an inactive
branch can be reused if the user switches back. `RECOMPUTE_TRIGGER_PATHS` is a deliberate
simplification — a `recompute_trigger` marker in the schema is the better home once more
fields influence enrichment.

---

## Open decisions

### O-002 — Optional decisions

How should `x-acdm-optional-decision` be scheduled relative to required-field completion: interleaved, section-level, or after required contract completion?

### O-003 — Schema/rules compatibility versioning

Define explicit versions for contract schema, rules DSL and action registry, and fail fast on incompatible combinations.

### O-004 — Datatype alias policy

Define which mappings (e.g. Oracle/SQL aliases -> contract datatypes) are deterministic policy and which require user confirmation/LLM inference.
