# Delivery stages 1–9

## Stage 1 — FastAPI and sessions

ADCM exposes `/health` and session endpoints. Session persistence is behind `SessionRepositoryPort`; the first adapter is in-memory. A session has an optional `user_id` so authenticated identity can later select user-specific configuration. In production this id must come from authentication, not arbitrary client input.

## Stage 2 — Mutable ContractState

`ContractState` uses JSON Pointer, supports arrays and later edits, keeps append-only user value history, authority and provenance. Direct/user-referenced values always outrank derived Forge suggestions.

## Stage 3 — Forge normalized domain

Forge owns `NormalizedContract`, normalized rules, requirements, issues and suggestions. Application services work on normalized models rather than the source `contract.json` representation.

## Stage 4 — isolated contract source and parser

Two separate ports are used:

- `ContractSourcePort` loads raw contract data;
- `ContractParserPort` maps one concrete format into `NormalizedContract`.

The current `contract_json_v1` parser is the only part that understands `$defs`, `$ref`, JSON Schema layout, `x-contract-rules` and `x-contract-rules-spec`. A future format should be implemented as another parser adapter without changing ADCM or Forge engines.

## Stage 5 — Forge evaluation and enrichment

Forge evaluates schema requirements, supported contract rules, defaults and enrichment. Enrichment uses `EnrichmentRepositoryPort` and normalized `EnrichmentRule` models. The current adapter reads JSON; repositories can be composed. Precedence inside Forge is USER enrichment > SYSTEM enrichment > GLOBAL enrichment. ADCM user/user-referenced values still outrank every Forge suggestion.

## Stage 6 — Forge MCP

`mcp-contract-forge` exposes stable `evaluate_contract(document, user_id?)`. `user_id` is context only and never becomes part of the generated contract. Forge remains deterministic and does not use PydanticAI.

## Stage 7 — ADCM ↔ Forge

ADCM calls Forge through mandatory `ContractForgePort`. The MCP transport is an outbound adapter. Forge is not exposed to the LLM as an optional tool because evaluation is an obligatory part of the stabilization algorithm.

## Stage 8 — PydanticAI heuristics

PydanticAI is used inside ADCM for structured evidence interpretation, requirement matching, semantic inconsistencies and question composition. Candidates must reference existing evidence; ADCM assigns authority/provenance from the evidence source rather than trusting the LLM to assign priority.

## Stage 9 — context tools, stabilization and YAML

The deterministic loop repeatedly calls Forge, applies derived values, asks PydanticAI to match existing evidence to newly discovered requirements, and repeats until no state changes. Optional context MCPs such as Atlassian, Schema Explorer, Repository and Visualizer are agent tools. They provide evidence or actions; Forge remains outside this optional toolset. Final YAML is generated only when formal validation and user-decision conflicts are resolved.

## Later stages

Logging remains separate after the functional core stabilizes:

- 10A application logging: local file adapter / GCP stdout adapter;
- 10B session audit logging: local JSONL adapter / BigQuery adapter.
