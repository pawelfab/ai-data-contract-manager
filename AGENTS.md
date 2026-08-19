# ADCM — instructions for coding agents

## 1. Read before changing code

Before planning, reviewing or implementing a change, read in this order:

1. `docs/CURRENT_STATE.md`
2. `docs/ADCM_CONTEXT.md`
3. `docs/ARCHITECTURE.md`
4. `docs/DECISIONS.md`

Then inspect the actual code relevant to the task. **Code is the source of truth for current implementation; these documents describe intent, constraints and known state.** If code and docs disagree, report the discrepancy before silently choosing one.

## 2. Core architectural rule

**ADCM is a thin orchestrator between the user/LLM and MCP Contract Forge. Contract Forge is the owner of the contract.**

ADCM may:
- conduct the conversation and keep conversation/session context;
- normalize imperfect user input;
- correct obvious typos and map aliases;
- parse pasted columns and other structured fragments;
- use deterministic heuristics first and LLM semantics when useful;
- call MCPs in a controlled loop;
- present Forge questions, validation issues and results to the user.

ADCM must not:
- independently decide whether a contract is valid;
- invent contract structure that Forge/schema did not expose;
- hardcode business defaults/enrichments that belong to Contract Forge;
- let the LLM mutate the canonical contract directly;
- let the LLM freely choose arbitrary contract paths to write;
- duplicate schema/rules logic in the UI.

Contract Forge must:
- own canonical contract state;
- interpret `contract.json` and enrichment rules;
- decide the active source variant;
- apply enrichments and JSON Schema defaults;
- discover current missing requirements;
- validate candidates and the final contract;
- expose enough provenance/diagnostics to explain why a value exists.

## 3. Required conversation flow

The intended stair-step flow is:

1. **Ask for source system first.**
2. Contract Forge selects/derives the source type when possible.
3. Forge applies **system-specific enrichment**.
4. Forge applies **generic enrichment**.
5. Forge applies **defaults from `contract.json`**.
6. Forge returns the next missing required information.
7. ADCM tries to satisfy it from already known facts:
   - deterministic heuristics,
   - previously provided user facts,
   - LLM semantic extraction/normalization.
8. If it cannot be safely resolved, ADCM asks the user a precise question.
9. Candidate values go back to Forge for validation.
10. Repeat until Forge reports complete/invalid.

The LLM does **not** control this loop. Code does.

## 4. Value precedence

Preserve this precedence unless an explicit architectural decision changes it:

`user > system enrichment > generic enrichment > JSON Schema default`

Deterministic and LLM extraction are methods of obtaining a user fact, not separate
business origins. A fact extracted by the LLM is submitted to Forge with `origin=USER`.

Enrichment should normally be fill-only and must not silently override a stronger source.

## 5. Dynamic contract requirement

`contract.json` is supplied by another module and may change. Avoid hardcoding individual contract fields in ADCM whenever they can be discovered from JSON Schema/Forge.

Expected dynamic behavior includes, within supported schema patterns:
- changed `required` fields;
- changed `default`, `enum`, `pattern`, descriptions and `x-acdm-question`;
- active source variants from discriminator/`oneOf`;
- standard JSON Schema validation.

A genuinely new business enrichment action/kind may require a Forge handler. Do not attempt to infer new executable semantics from free-form `message` text.

## 6. User-input normalization rule

ADCM should be forgiving about representation but conservative about meaning.

Examples it should handle or progressively clarify:
- source-system typos such as `roket` -> `rocket`;
- identifiers with spaces/case needing canonicalization;
- pasted columns as JSON, CSV-like text, SQL/Oracle/BigQuery-like definitions, or multiline lists;
- information provided before Forge asks for it;
- incomplete structured input: preserve partial facts and ask only for what is missing instead of repeating the whole question.

Do not fabricate a datatype or business value when the user did not provide enough evidence. A default such as `STRING` is acceptable only if the contract/rules explicitly define it or the user explicitly approves such a UX convention.

## 7. MCP boundaries

Current/future responsibilities:

- **Contract Forge MCP** — contract structure, rules, enrichments, validation, pending requirements.
- **Schema Explorer MCP** — environment facts such as BigQuery schema/table existence, naming standards and repository/YAML discovery.
- **ADCM** — sequencing, conflict resolution between MCP results, user interaction and semantic normalization.

MCPs should not be coupled by direct MCP-to-MCP calls by default. ADCM/application orchestration should pass required context between them.

## 8. Change workflow

For a question about existing behavior:
- inspect docs and code;
- answer from current implementation;
- do not edit code unless asked.

For a planning request:
- inspect current code first;
- produce a plan with concrete files/classes/functions;
- do not implement unless asked.

For an implementation request:
- make the smallest change that satisfies the requested behavior;
- preserve the ownership boundaries above;
- add/update tests before considering the task complete;
- run the relevant tests;
- update `docs/CURRENT_STATE.md`;
- update `docs/DECISIONS.md` only when an architectural/product decision changed.

Avoid broad rewrites for a local bug. Avoid adding framework layers that are not required by the current vertical slice.

## 9. Documentation maintenance

After meaningful code changes, update `docs/CURRENT_STATE.md` with:
- what changed;
- current execution path;
- known limitations/failing tests;
- important files/classes;
- next concrete work.

When a durable architectural rule changes, add an entry to `docs/DECISIONS.md` with status, rationale and consequences.

Use `docs/UPDATE_CHECKLIST.md` before finishing an implementation task.
