# Consolidated architecture decisions

## D-01 Independent services
ADCM and each MCP are independently versioned/deployed Python services with their own pyproject, environment, tests and Dockerfile. No cross-service Python imports.

## D-02 Contract-format isolation
Only the Contract Forge contract adapter knows `$defs`, `$ref`, `x-contract-rules`, and the concrete JSON layout. Schema path changes must not propagate into ADCM.

## D-03 Semantic anchors
Domain concepts needed by Forge services are exposed by `ContractSemanticPaths`; their concrete JSON Pointers are supplied by the contract-format adapter. `source_system` currently maps to `/metadata/sourceSystemGcpId`.

## D-04 Progressive discovery
JSON Schema defines final validity. A separate discovery policy controls which fillable requirements are visible now. ADCM has no stage-specific contract-path logic.

## D-05 Discovery repository is synchronous
Forge evaluation, enrichment repositories and MCP tool are synchronous. `DiscoveryPolicyRepositoryPort.get_policy()` is synchronous until real per-call async I/O makes a Forge-wide async conversion worthwhile.

## D-06 Fillable vs structural requirements
Structural parents are formal requirements but not user-fillable questions when required child requirements exist. The fillable filter is a Forge responsibility before discovery.

## D-07 Progressive derived values
Defaults/enrichment should not activate hidden future branches. Only currently visible/eligible targets (or already-existing targets being recomputed) receive suggestions.

## D-08 Enrichment storage vs matching
Repositories may use context to efficiently fetch candidate rules. They do not decide whether a rule is active. Runtime scope/system/user/condition matching belongs to `EnrichmentResolver`.

## D-09 Global templates
Global enrichment supports `{/json/pointer}` copy/interpolation and target path patterns. Source system may therefore be copied to `metadata.id` and any later-discovered `systemZrodlowy` without per-system duplicate Python or JSON rules.

## D-10 Derived values are disposable/recomputed
ADCM stores user and derived values separately. Derived values are replaced from each Forge evaluation, not accumulated forever. User changes therefore re-evaluate enrichments/defaults.

## D-11 LLM produces candidates, not mutations
Every LLM candidate references Evidence. ADCM validates evidence/path/type/structure/authority deterministically before `ContractState` changes.

## D-12 Candidate decision and progress are separate
An accepted candidate may repeat an existing value. `CandidateOutcome.changed` is the only signal used for fixed-point progress.

## D-13 Containers cannot be silently destroyed
A scalar candidate cannot replace an existing dict/list container. `set_pointer()` also raises a domain `JsonPointerError` on scalar intermediate traversal as the final defensive boundary.

## D-14 Authority
Application policy currently ranks:

```text
USER_DIRECT > USER_REFERENCED > SYSTEM_RULE > OBSERVED_CONVENTION > DEFAULT
```

Forge-derived enrichment/defaults live in the derived layer and never override accepted user values.

## D-15 Complete does not lock editing
`valid=True` is validation state, not workflow terminal state. A new chat message still gets one semantic-resolution pass so existing fields can be changed.

## D-16 Warnings are current state
Warnings returned by API are the final fixed-point snapshot. Historical round diagnostics belong to future audit/session logging.

## D-17 Missing fields are not semantic warnings
Forge owns missing requirements. LLM consistency checks are reserved for actual semantic contradiction, suspicious mismatch, typo or conflicting evidence.

## D-18 PydanticAI compatibility
For structured heuristic outputs, use `PromptedOutput` by default to support OpenAI-compatible endpoints without tool/function calling.

## D-19 Attachments today are inline text
`attachments: list[str]` means pasted text, not path or ID. File upload will be a future inbound/extractor boundary.

## D-20 Do not implement VALIDATION_REGISTRY prose semantics
Custom `x-contract-rules` without machine-readable assertion/condition remain unsupported/informational. Do not parse business logic out of `message`, `description` or `notes` text.
