# ADCM — project context

## 1. Purpose

ADCM is a conversational assistant for building data contracts for ingestion/medallion pipelines. Its main UX goal is to **lead the user through contract creation without forcing the user to understand the full schema at once**.

The system should feel like a guided conversation, while the contract remains deterministic and governed by Contract Forge MCP.

The minimal product path is intentionally narrow:
- terminal chat first;
- API already/soon available so a web UI can be added later without moving orchestration logic to the frontend;
- initial demonstration may support only a small number of source systems, but the architecture must not bake those systems into ADCM.

## 2. Fundamental product behavior

The conversation starts with the source system because this unlocks system-specific enrichment and determines which source branch is relevant.

High-level order:

```text
User
  -> ADCM asks/selects source system
  -> Contract Forge selects source variant/type
  -> system-specific enrichment
  -> generic enrichment
  -> contract.json defaults
  -> missing required fields
  -> ADCM resolves from history/heuristics/LLM or asks user
  -> Forge validates candidate
  -> repeat
```

The important property is **progressive discovery**. Forge may require several choices one after another. ADCM/LLM can already know later facts from an earlier user message and should reuse them when the corresponding requirement becomes visible.

## 3. Why ADCM is not the contract engine

Earlier experiments put too much enrichment/recommendation behavior in ADCM. That makes the conversational application dependent on one specific contract shape and causes duplicated business rules.

The target split is:

### ADCM owns interaction
- session/conversation flow;
- user-facing questions and explanations;
- semantic interpretation of user input;
- deterministic input cleanup and parsing;
- orchestration of MCP calls;
- reuse of facts from conversation history;
- future web API/UI boundary.

### Contract Forge owns contract semantics
- schema knowledge;
- contract state;
- enrichment rules;
- defaults;
- active variants;
- required-field discovery;
- candidate validation;
- final validation;
- provenance of values.

This lets `contract.json` evolve without requiring every schema change to modify ADCM.

## 4. Role of heuristics

Heuristics should handle cheap, deterministic transformations before calling an LLM. This reduces cost and makes obvious behavior predictable.

Examples:
- fuzzy source system matching;
- identifier canonicalization;
- URI extraction;
- booleans/integers/enums;
- parsing columns from common pasted formats;
- normalizing common datatype aliases where the mapping is deterministic and agreed.

Heuristics should support **partial extraction**. Example:

User pastes:

```text
data_d, sap1, sap2, sap3
```

If the contract requires `name + dataType`, ADCM should retain the four names and ask for missing types. It should not discard the partial result and repeat the original question unchanged.

## 5. Role of the LLM

LLM is a semantic resolver, not an autonomous contract agent.

Good LLM tasks:
- extract a fact the user already stated before Forge exposed its path;
- understand noisy or natural-language answers;
- map a pasted definition into a candidate structure;
- normalize type/name representations when deterministic parsing fails;
- explain a validation error to the user in plain language.

LLM restrictions:
- only answer paths currently allowed/exposed by Forge (or use an explicit controlled partial-fact mechanism);
- never directly mutate canonical contract state;
- never bypass Forge validation;
- do not invent values with no evidence.

## 6. Contract/rules are versioned inputs

`contract.json` can change because another module provides it. Enrichment rules can also evolve.

Therefore the runtime should distinguish:
- structural changes the generic schema navigator can understand;
- new executable rule semantics that require a registered Forge handler;
- incompatible old rules that refer to paths no longer present in the schema.

A compatibility gate/version should eventually prevent a mismatched schema/rules pair from partially executing without a clear diagnostic.

## 7. Known schema/rules history

The currently supplied contract uses a root structure with, among others:

```text
metadata
source
targets.bronze
targets.silver (optional)
targets.gold (optional)
orchestration
converter (optional)
preparator (optional)
```

An older enrichment file used paths such as:

```text
bronzeTable
silver.tables[]
gold.entries[]
converter.source.*
rawData
```

These are not equivalent by name alone. ADCM must not guess mappings. Migration/compatibility belongs with Contract Forge/rules maintenance.

Other known inconsistencies from the supplied artifacts:
- old rules used `@daily`, while the current contract schedule pattern requires a five-field cron;
- fixed-width rule text mentioned `length = end - start + 1`, while the current source column model uses a half-open `[start,end)` range and does not expose a `length` field;
- some `x-contract-rules` rely on semantic meaning hidden in `message`/`id` rather than a fully machine-readable condition/assertion structure.

## 8. Schema Explorer — planned second MCP

Schema Explorer is intended to supply environment/repository knowledge, for example:
- BigQuery project/dataset/table existence;
- naming rules;
- column/schema lookup;
- existing YAML contracts in a repository;
- loading an existing contract for modification.

Contract Forge should remain the contract rules engine. Schema Explorer contributes environment facts/recommendations. ADCM coordinates both and presents conflicts or choices to the user.

## 9. Transport/deployment direction

Current/minimal form:
- CLI terminal;
- FastAPI boundary for future web UI;
- local in-process Forge adapter for fast tests/demo;
- MCP Streamable HTTP for real separation.

Target deployment context discussed for the wider project includes Cloud Run. For production, in-process session dictionaries are not sufficient when instances scale; session state needs a durable/shared store.

## 10. Product priorities

When choosing between architectural completeness and a working demo:
1. keep the ownership boundaries correct;
2. deliver one or two complete vertical slices;
3. prefer a small deterministic controller over a large dynamic framework that does not work yet;
4. only generalize once the real behavior has stabilized.
