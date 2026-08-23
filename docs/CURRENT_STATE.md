# ADCM current state — consolidated v0.4

## Scope

This package consolidates the architectural decisions and runtime fixes made after the previous v4 guardrails package.

The two runtime services remain independent:

```text
ai-data-contract-manager
        |
        | ContractForgePort / MCP Streamable HTTP
        v
mcp-contract-forge
```

ADCM owns conversation/session/evidence/user-value state and the deterministic fixed-point loop. Contract Forge is stateless per call and owns interpretation of the contract schema, rules, defaults, enrichment and progressive requirement discovery.

## Conversation flow

```text
user evidence
   ↓
ADCM session/evidence
   ↓
Forge.evaluate(document)
   ↓
formal requirements
   ↓
fillable filter
   ↓
discovery policy
   ↓
visible requirements
   + progressive defaults/enrichment
   ↓
ADCM applies derived suggestions
   ↓
LLM proposes evidence-backed candidates
   ↓
deterministic candidate validation
   ↓
ContractState
   ↓
repeat until fixed point
```

### First gate

The first visible requirement is always the semantic anchor `@sourceSystem`, mapped by the current contract adapter to:

```text
/metadata/sourceSystemGcpId
```

The mapping is owned by `contract_json_v1/semantic_paths.py`; ADCM never knows this path.

## Discovery

`resources/discovery_rules.json` is UX/discovery policy, not validation schema.

Current stages:

1. source system only;
2. remaining metadata (`id`, `version`, `dataFileId`);
3. orchestration (`schedule`, `startDate`);
4. all remaining currently formal/fillable requirements.

The engine supports N stages and `whenAnyMissing`, so stages can be refined by data without changing ADCM.

Final `valid` is always calculated from the complete formal requirement set, never from only visible requirements.

## Enrichment

`resources/ux_rules.json` is normalized by `JsonEnrichmentRepository` and evaluated by `EnrichmentResolver`.

Key invariants:

- repository adapters map/fetch rules; runtime match decisions live in `EnrichmentResolver`;
- SYSTEM rules require a known matching `EnrichmentContext.source_system`;
- USER rules require matching user context;
- GLOBAL rules are system-independent;
- hidden/later target paths are not materialized early: enrichment is limited to currently visible/eligible paths (or an already-existing target being recomputed);
- derived values are recomputed from the current Forge result each round; stale SAP values cannot survive a later source-system change.

### Template/copy syntax

A global enrichment can copy another field:

```json
{
  "path": "/metadata/id",
  "value": "{/metadata/sourceSystemGcpId}"
}
```

If the whole string is one `{/json/pointer}` placeholder, the source value is copied with its original type.

String interpolation is also supported:

```json
{
  "path": "/rawData/gcsBucketPath",
  "value": "gs://landing/{/metadata/sourceSystemGcpId}/{/metadata/dataFileId}"
}
```

Only braces containing an absolute JSON Pointer are treated as enrichment placeholders, so unrelated template syntax such as `{{date}}` is left untouched.

A target pattern can fill a field wherever it becomes a visible requirement:

```json
{
  "pathPattern": "/**/systemZrodlowy",
  "value": "{/metadata/sourceSystemGcpId}"
}
```

This is how the same source-system value can be copied into source-specific technical metadata only after those branches are discovered.

## Fillable requirements

The SchemaEngine remains formal and may return structural parents such as `/metadata` plus children.

Before discovery, `fillable_requirements()` removes a requirement that is a strict JSON-Pointer ancestor of another current requirement. This keeps `/metadata/id` and `/metadata/version`, but prevents LLM from being asked to fill `/metadata` as a scalar/object blob.

Arrays/objects that are actual fillable leaves remain visible, e.g. an entire required `columns` array when the schema expects that array as a value.

## Candidate safety

LLM never writes state directly. It returns `Candidate` objects referencing evidence.

`ValueResolver.apply_candidates()` returns `CandidateOutcome` containing decisions and a separate `changed` flag.

Statuses:

- `ACCEPTED`
- `SHADOWED`
- `REJECTED`
- `NEEDS_USER_DECISION` (reserved; no conflict policy produces it yet)

Checks include:

1. evidence exists;
2. confidence threshold;
3. path is current requirement / legal structural descendant, or already exists for an explicit edit;
4. type agrees with Forge requirement when known;
5. scalar cannot replace an existing dict/list container;
6. trial full-document build must succeed;
7. lower-authority evidence cannot overwrite stronger user evidence.

A rejected candidate is ephemeral, does not alter `ContractState`, and does not create a user warning. The underlying evidence remains.

`ACCEPTED` does not imply progress. Repeating the same effective value produces `changed=False`, which prevents endless stabilization loops.

## Editing after complete

On the first round of every new user message, the semantic resolver is called even when Forge has no unresolved requirement. This permits explicit edits to existing fields after `valid=True`.

Later automatic rounds resolve only newly visible missing requirements.

Arrays can be edited by returning the whole existing array value when adding/changing elements and no narrower current requirement exists.

## Warnings

User-visible warnings are a snapshot of the final stable round, not an accumulation across all internal rounds.

Missing required fields belong to Forge and must not be reported as heuristic inconsistency warnings.

## Question presentation

Forge requirements carry:

- path;
- title/description from schema;
- optional discovery `displayName` / `helpText` overrides.

Question generation must not invent business meanings. Ambiguous identifiers are shown with their canonical path, e.g.:

```text
Data File ID (/metadata/dataFileId)
```

The source-system discovery policy overrides the raw schema title to user-facing `System źródłowy` while preserving the canonical path in the structured requirement.

## PydanticAI/local OpenAI-compatible models

The heuristic adapter uses `PromptedOutput`, avoiding tool-based structured output for local APIs that do not implement tool calls.

Optional configuration:

```env
ADCM_LLM_MODEL=gpt-4o
ADCM_LLM_BASE_URL=http://127.0.0.1:1234/v1
OPENAI_API_KEY=local
```

The local OpenAI-compatible provider uses `OpenAIChatModel` + `OpenAIProvider`.

## Attachments

Current API:

```json
{
  "content": "...",
  "attachments": ["inline attachment text"]
}
```

Each element becomes its own `EvidenceItem(source_type="attachment_text")`.

There is no file upload in this version. Future upload must be implemented as a new inbound upload adapter plus `FileContentExtractorPort`, producing the same Evidence model without changing the stabilization loop/heuristics.

## Contract source

Forge has one runtime contract source: `mcp-servers/mcp-contract-forge/resources/contract.json`.

`test_source_linter.py` verifies that the checked-in source has no dangling local `$ref` values. `contract.input.json` is no longer present in runtime resources, so there is no competing historical contract file for Forge to load.

## Known future work

Not implemented yet:

- real file upload/extractors;
- persistent session storage;
- application + session audit logging adapters (planned stage 10);
- `NEEDS_USER_DECISION` conflict-resolution policy;
- production user-enrichment storage (current user repository is no-op/reference memory adapter);
- deterministic partial-fact store for incomplete column lists; current LLM can form structured candidates but partial column-name-only facts are not yet a separate durable model;
- real E2E verification against the user's concrete local OpenAI-compatible server and deployed MCP endpoints.
