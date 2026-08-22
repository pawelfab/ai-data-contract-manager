# ADCM consolidated analysis — v0.4

This document consolidates the architecture decisions and failure modes discovered during the ADCM/Contract Forge implementation and live API testing.

## 1. Product goal

ADCM is a guided conversation for building a data-contract YAML without requiring the user to understand the entire schema at once. The deterministic source of contract semantics is Contract Forge. The desired UX is progressive: source system first, then only the currently relevant groups of fields, while reusing facts already supplied earlier in the conversation.

## 2. Service ownership

### ADCM owns

- chat/session and EvidenceStore;
- user-value history, authority and provenance;
- semantic interpretation through PydanticAI;
- deterministic acceptance/rejection of LLM candidates;
- fixed-point orchestration of mandatory Forge calls;
- user-facing questions, warnings and rendering.

### Contract Forge owns

- contract source loading/parsing;
- normalized schema/rules semantics;
- formal requirements and defaults;
- supported executable `x-contract-rules` semantics;
- enrichment repository + resolver;
- progressive requirement discovery;
- final validity and deterministic issues.

No runtime imports cross the service boundary.

## 3. Contract evolution

Raw `contract.json` is isolated behind `ContractSourcePort -> ContractParserPort -> contract_json_v1`. ADCM never knows `$defs`, `$ref`, rule layout or canonical contract paths. Semantic anchors such as `source_system` belong to the format adapter.

The currently supplied latest contract file still contains dangling local `$ref` references. This package preserves it unchanged as `resources/contract.input.json` and uses a separately documented runtime repair. The inferred repaired definitions are a compatibility fixture, not authoritative business schema.

## 4. Progressive discovery

Earlier Forge returned the complete final required set immediately. That produced broad questions and allowed later sections to appear before their prerequisites. The fix separates:

```text
formal requirements -> fillable filter -> discovery policy -> visible requirements
```

`valid` is always based on full formal requirements. Discovery is configurable in `resources/discovery_rules.json`; ADCM contains no stage/path workflow.

Current default flow:

1. source system only;
2. remaining metadata;
3. orchestration;
4. remaining formal requirements.

## 5. Source-system semantics and enrichment

For contract-json v1 the semantic source-system anchor is `/metadata/sourceSystemGcpId`. It drives `EnrichmentContext.source_system`.

A previous bug applied SAP enrichment with no selected system. The adapter now only maps persisted rules; runtime scope/system/user matching is exclusively the responsibility of `EnrichmentResolver`.

Global enrichment supports reusable copy/template semantics rather than duplicating rules per system. The current rules copy the chosen source system into `metadata.id` and can populate later-discovered `systemZrodlowy` fields through a path pattern. System-specific rules remain for genuinely system-specific values.

Enrichment targets are gated by current discovery/existing paths so a later rule cannot create a section prematurely.

## 6. Fillable requirements

Schema engines may formally emit both a container and its required children, e.g. `/metadata` plus `/metadata/id`. Structural parents are not useful LLM questions and invite invalid scalar writes. `fillable_requirements` therefore removes strict ancestor requirements when children represent the actual fillable values. Genuine fillable arrays/objects remain.

## 7. Candidate safety

A live failure showed that the LLM may invent or shorten a path even when Forge did not expose it. Therefore LLM output never mutates state directly.

Candidate validation checks:

- evidence reference exists;
- confidence threshold;
- path is currently legal or is an existing field being explicitly edited;
- descendant writes are allowed only for structural requirements;
- value type matches Forge expectation when available;
- scalar writes cannot destroy existing containers;
- full trial effective-document build succeeds;
- weaker authority cannot replace stronger user authority.

Rejected candidates disappear after the round; evidence remains. They are internal behavior, not automatically user warnings.

## 8. JSON Pointer structural failures

The original `set_pointer` could descend into a scalar and raise a raw `TypeError`. It now raises `JsonPointerError`. Trial-building alone was not sufficient because replacing an existing object with a scalar can technically succeed while deleting children; an explicit container-destruction guard is therefore required before mutation.

## 9. Stabilization convergence

`ACCEPTED` does not mean state changed. Repeating the same already-effective candidate is accepted but idempotent. `CandidateOutcome.changed` is separate from status and fixed-point progress depends only on actual mutation.

Derived values are recomputed/replaced from current Forge suggestions on each round. This prevents stale system-derived values surviving a later change of source system.

`valid` is not a terminal workflow state. A new user message after completion still gets one semantic-resolution pass so existing fields can be edited.

## 10. Warnings and questions

Warnings returned by the API are the current fixed-point snapshot, not an accumulation across stabilization rounds. Missing fields belong to Forge requirements and are not semantic inconsistency warnings.

Questions use Forge/schema presentation metadata and canonical paths. The LLM must not invent meanings such as “configuration ID” when the schema only says `metadata.id`. Ambiguous identifiers should retain the canonical path in the question.

## 11. Natural-language normalization

The semantic resolver may normalize an unambiguous user expression into a standard representation required by the contract (for example “every day at 7am” to a five-field cron) but must not guess when meaning is ambiguous. Deterministic validation still decides whether the candidate is accepted.

## 12. PydanticAI/local model compatibility

The user environment includes an OpenAI-compatible endpoint without tool-call support. Structured outputs therefore use PydanticAI `PromptedOutput`, with `OpenAIChatModel` and `OpenAIProvider` for configurable base URL/API key. Settings load `.env` relative to the ADCM service directory rather than process cwd.

## 13. Attachments and future uploads

Current API `attachments: list[str]` contains inline textual content. Each item becomes separate `attachment_text` evidence. It is not a path or upload ID.

Future file upload should add an inbound endpoint and `FileContentExtractorPort`; it should not redesign EvidenceStore, heuristics or stabilization.

## 14. Known historical problems retained as guardrails

- old enrichment files and newer contract layouts can diverge; never infer path migration in ADCM;
- some `x-contract-rules` contain semantics only in prose and cannot be generically executed safely;
- fixed-width historical rule semantics have conflicted with schema structure;
- source-column partial-input UX still deserves a dedicated partial-fact mechanism rather than accepting invalid canonical columns;
- real persistence/session audit, production logging and context MCP conflict policy are intentionally later stages;
- real MCP + local/production LLM E2E must be verified in the target environment in addition to deterministic unit tests.

## 15. Architecture stop conditions

Stop and redesign if any change requires:

- ADCM domain/application code to know a concrete contract path;
- a contract format change to propagate beyond the Forge format adapter without changed normalized semantics;
- an enrichment storage change to modify Forge core evaluation;
- LLM code to decide final validity/priority/state mutation;
- a new optional context MCP to rewrite the mandatory Forge stabilization loop.
