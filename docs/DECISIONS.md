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

**Value precedence:** explicit user > LLM-extracted user fact > system enrichment > generic enrichment > schema default.

**Consequence:** Lower-priority mechanisms must not overwrite stronger values silently.

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

**Decision:** Forge exposes an input mode for each requirement. Schema-defined fields
use `x-acdm-input-mode: explicit` when they must be answered through deterministic
parsing/Pydantic and Forge validation without LLM extraction. Generated workflow
gates may set the same mode directly. All other requirements default to `semantic`.

**Why:** Source selection and core identifiers determine later branches and future
repository lookups. They must remain predictable, auditable and explicitly confirmed.

**Consequence:** ADCM may invoke the LLM only for the semantic prefix before the next
explicit gate; it never sends an explicit requirement to the semantic resolver.
The current source-system gate, source-type discriminator and `metadata.id` are
explicit. A future `dataFieldId` receives the same behavior through schema metadata;
ADCM does not create that field while it is absent from `contract.json`.

---

## Open decisions

### O-001 — Partial facts protocol

Should partial structured information be stored only in ADCM memory, or should Forge expose a formal draft-partial protocol? Current preference: keep invalid partial structures outside the canonical contract until a clear Forge protocol exists.

### O-002 — Optional decisions

How should `x-acdm-optional-decision` be scheduled relative to required-field completion: interleaved, section-level, or after required contract completion?

### O-003 — Schema/rules compatibility versioning

Define explicit versions for contract schema, rules DSL and action registry, and fail fast on incompatible combinations.

### O-004 — Datatype alias policy

Define which mappings (e.g. Oracle/SQL aliases -> contract datatypes) are deterministic policy and which require user confirmation/LLM inference.
