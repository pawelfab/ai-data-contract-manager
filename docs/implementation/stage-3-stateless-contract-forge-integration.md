# Stage 3 — Real stateless Contract Forge transport and provider conformance

## Goal

ADCM can call an authoritative Contract Forge through a provider adapter using the three stateless operations and typed models already established. Forge compiles canonical paths and aliases, evaluates progressive requirements/defaults/enrichments/rules, reports explicit priority/specificity and dependencies, validates final drafts, preserves runtime Contract DSL, and enforces schema-revision consistency. ADCM remains a consumer/orchestrator; it does not gain a schema or enrichment evaluator.

## Why this stage exists

The current `MockContractForgeAdapter` is intentionally a staged demo. `contracts/contract.json` is a migration/reference JSON Schema with canonical converter/preparator paths, while `examples/contract-rules.json` remains a 12-rule legacy catalog with alias/path differences. The requested local `contracts/ux_rules.json` bundle now exists, but no production Forge source, agreed endpoint, or transport contract is present in this repository. A real integration cannot be implemented safely until those external inputs are supplied and their ownership/protocol are confirmed.

## Preconditions

- Stage 2 fast-forward and revision handling pass with the mock adapter.
- The Forge owner supplies all of the following in writing: authoritative schema source, authoritative enrichment source or repository/endpoint (the local `contracts/ux_rules.json` is only a fixture), transport/protocol (including authentication and error envelope), schema revision semantics, and rule priority/specificity contract.
- The owner identifies whether the local `contracts/contract.json` is a fixture, a versioned production artifact, or to be retired. Until then it remains a fixture only.
- The supplied schema/enrichment package includes an explicit alias-normalization policy and a generic fallback for unknown systems.
- If any precondition is false, stop and report `BLOCKED_INPUT`; do not reconstruct missing rules from examples or documentation.

## Scope

- Add a production transport adapter implementing `ContractForgePort` behind the existing port (for example `src/adcm/adapters/mcp/contract_forge.py`).
- Define/verify typed request and response serialization for `ContractInput`, `ContractEvaluationResult`, `FinalValidationResult`, `RenderRequest`, and `RenderedContract`.
- Conformance-test canonical schema paths, alias normalization (including snake_case-to-camelCase), ambiguous/unknown alias failure, progressive `CurrentSchemaView` replacement, and schema revisions.
- Keep Forge-side precedence between its own rules explicit through priority/specificity metadata; ADCM origin precedence remains in `CandidateResolver`.
- Implement or verify Forge-owned enrichment/default/derived candidate behavior, unknown-system generic fallback, and deferred capability dependencies using the supplied authoritative bundle.
- Verify `{source}` enrichment-time placeholders and preservation of runtime `{{env}}`, `{{date:%Y%m%d}}`, and `{{var.name}}`.
- Verify final validation and canonical YAML rendering are separate operations and require the expected schema revision.

## Out of scope / Do not do

- Do not parse or evaluate the schema, `x-contract-rules`, or enrichment data in `src/adcm`.
- Do not add a stateful Forge session, `submit_values`, hidden server-side draft, or background validation loop.
- Do not let Forge call Schema Explorer, registry, repository lookup, or any other MCP directly; return `CapabilityRequest` for ADCM routing.
- Do not move origin precedence, candidate resolution, user prompting, or `WorkflowOutcome` decisions into Forge.
- Do not consume runtime Contract DSL in ADCM or Forge; Airflow DAG Generator owns translation later.
- Do not mark this stage complete while the production Forge source, endpoint, or transport contract remains unresolved.

## Architectural boundaries

- **ADCM adapter/port:** serializes typed stateless requests, sends them to Forge, validates response envelopes, and maps transport failures to explicit application errors.
- **Contract Forge:** owns schema authority, canonical paths/aliases, progressive view, required fields, defaults, enrichment rules, internal rule conflicts, validation, and YAML.
- **LLM:** supplies semantic proposals only and is never consulted for path authorization or rule evaluation.
- **Other MCPs:** are orchestrated by ADCM; Forge returns dependency/capability requests but never invokes them.
- **Airflow DAG Generator:** consumes runtime DSL after Forge rendering and is outside this transport.

## Invariants

- Forge is stateless from ADCM's perspective; every call receives the current draft snapshot and capability results.
- `ContractInput` does not contain `ConversationState`, chat history, evidence history, unbound signals, or superseded candidates.
- `CurrentSchemaView` is a complete replacement snapshot and includes an opaque `schema_revision`.
- No path is legal in ADCM without current Forge authorization.
- Schema wins over semantic inference; unknown system-specific enrichment falls back to generic rules where the Forge contract permits.
- Forge reports internal priority/specificity; ADCM resolves origin precedence.
- Runtime `{{...}}` DSL is preserved verbatim.

## Files affected

| File | Action | Purpose |
|---|---|---|
| `src/adcm/ports/contract_forge.py` | MODIFY | Document/validate the provider-neutral stateless contract and typed transport error boundary. |
| `src/adcm/domain/models.py` | MODIFY if response fields require it | Represent authoritative rule priority/specificity, dependencies, schema revision, and render receipts without leaking provider payloads. |
| `src/adcm/adapters/mcp/contract_forge.py` | NEW | Implement the selected remote/local Forge transport; no schema evaluator. |
| `src/adcm/adapters/mcp/mock_contract_forge.py` | MODIFY | Keep the fixture adapter conformant and clearly separate from production transport. |
| `src/adcm/config.py` | MODIFY | Add endpoint/transport/auth-reference settings as opaque configuration, with safe mock defaults. |
| `tests/test_contract_forge_transport.py` | NEW | Contract tests for serialization, status/revision errors, and transport failures. |
| `tests/test_contract_forge_integration.py` | NEW | Real authoritative schema/enrichment conformance tests supplied by the Forge owner. |
| `tests/fixtures/` | NEW only for owner-approved sanitized fixtures | Store versioned response fixtures, never hidden production secrets or invented enrichment rules. |
| `docs/MCP_CONTRACT.md` | MODIFY | Record the confirmed wire contract and error envelope. |
| `docs/ISSUES_AND_RESOLUTIONS.md` | MODIFY | Record alias, rule-priority, enrichment, and revision resolutions. |
| `docs/DESIGN_DECISIONS.md` | MODIFY | Record the external source/ownership decision. |
| `docs/architecture/modules/ports.md` | MODIFY | Synchronize the provider-neutral port. |
| `docs/architecture/modules/adapters.md` | MODIFY | Describe the real adapter separately from the mock. |

## Public contracts

The logical operations remain:

```python
async def evaluate_draft(request: ContractInput) -> ContractEvaluationResult: ...
async def validate_final(request: ContractInput) -> FinalValidationResult: ...
async def render_yaml(request: RenderRequest) -> RenderedContract: ...
```

`ContractInput` contains the current nested draft, prior `CapabilityResult` values, and optional `expected_schema_revision`. `ContractEvaluationResult` contains only `INCOMPLETE | COMPLETE | INVALID`, a complete `CurrentSchemaView`, requirements, Forge `ExternalCandidate` values with provenance and rule priority/specificity, validation findings, and capability requests. `FinalValidationResult` contains `VALID | INVALID | DEFERRED_EXTERNAL`, findings, and requests. `RenderRequest` carries a draft, expected revision, and `RenderMode.DRAFT | FINAL`.

Transport-specific headers, auth, retries, and wire envelopes stay private to the adapter. The application sees typed errors such as configuration failure, schema revision mismatch, transport unavailable, malformed response, and provider validation failure.

## Inputs and outputs

The adapter accepts JSON-serializable nested drafts and capability results. It returns typed Pydantic models after validating the provider response. It must preserve arbitrary runtime template strings, candidate evidence/provenance metadata supplied by Forge, and dependency details for deferred findings. It must not return hidden model reasoning or untyped provider state.

## State ownership

Forge may cache immutable schema/enrichment artifacts behind its own port or service, but no onboarding session or draft state is stored there. ADCM owns the current draft, candidates, signals, evidence, revisions, and capability results. The transport adapter owns only connection/session lifecycle required by its protocol and must not persist workflow state.

## Data flow

```text
ADCM ContractInput + expected revision
        -> provider-neutral ContractForgePort
        -> remote/local Forge transport
        -> schema view + requirements + Forge candidates/findings/requests
        -> typed validation in adapter
        -> WorkflowRunner replaces view and continues
```

## Required behavior / how it should work

1. Compile and normalize rule paths inside Forge. Canonical schema paths are the only paths returned to ADCM.
2. Reject unknown aliases and fail configuration loading on ambiguous aliases; never choose an alias by insertion order.
3. Evaluate progressive requirements and defaults against the supplied snapshot. Defaults are candidates; if a default activates a new required rule, the next evaluation reports that requirement.
4. Preserve all Forge candidates needed by ADCM resolution and return explicit internal rule priority/specificity. Do not collapse candidates into a single value before ADCM applies origin precedence.
5. Return a complete current schema view on every evaluation. A branch correction replaces the prior view and allows ADCM to reproject away illegal fields.
6. Return `DEFERRED` findings with a typed dependency (`FIELD`, `CAPABILITY`, or `WORKFLOW`) and enough context for ADCM to request a capability or user value.
7. Apply generic fallback rules when a system-specific enrichment is unknown, unless the authoritative Forge contract marks the system as invalid.
8. On every call with `expected_schema_revision`, reject a mismatch explicitly; do not silently evaluate against a newer revision.
9. Keep `{source}` enrichment placeholders resolvable by Forge while emitting runtime `{{...}}` DSL unchanged.
10. Render canonical YAML only through `render_yaml`; do not attach YAML to evaluation responses.

## Forbidden implementation shortcuts

- Implementing a local `jsonschema`/rule evaluator in `src/adcm` “temporarily”.
- Merging the local legacy rule catalog with the production bundle without an owner-approved mapping.
- Returning a top-level `DEFERRED`, `WAITING_FOR_USER`, or `BLOCKED_EXTERNAL` from Forge.
- Returning snake_case aliases to ADCM and relying on application code to guess canonical paths.
- Hiding provider revision mismatches behind automatic retries that change the expected token.
- Dropping rule scope/priority or evidence because a wire format is inconvenient.

## Error semantics

- Missing endpoint/bundle/auth configuration: deterministic configuration error; Stage 3 remains blocked until corrected.
- Timeout/unavailable transport: typed provider-unavailable error; ADCM maps required unresolved capability to `BLOCKED_EXTERNAL`.
- Malformed provider response: protocol/conformance error; never fabricate defaults or findings.
- Alias unknown/ambiguous or schema-rule configuration invalid: Forge configuration error with path/alias/rule ID.
- Expected revision mismatch: explicit schema-change error; the caller must surface it and not merge results.
- Provider final validation invalid/deferred: typed result, not transport failure.

## Status semantics

Exactly:

```text
evaluate_draft: INCOMPLETE | COMPLETE | INVALID
finding:        VALID | INVALID | DEFERRED
validate_final: VALID | INVALID | DEFERRED_EXTERNAL
```

ADCM remains the owner of `WAITING_FOR_USER`, `BLOCKED_EXTERNAL`, `COMPLETE`, `INVALID`, and `FAILED` workflow outcomes.

## Schema revision semantics

Forge returns `CurrentSchemaView.schema_revision` and `FinalValidationResult.schema_revision`. ADCM sends the accepted revision back as `expected_schema_revision` on every subsequent call. A revision change invalidates in-flight assumptions and must be surfaced as a schema-change condition. `draft_hash` remains a hash of canonical draft content only.

## Rendering semantics

`RenderMode` has exactly `DRAFT` and `FINAL`. FINAL rendering is permitted only after a VALID final-validation receipt for the same draft hash and schema revision. The adapter renders after fast-forward stabilization; cache policy belongs to the application render service.

## Template semantics

Forge resolves enrichment-time placeholders such as `{source}` using authoritative enrichment data. It must preserve runtime Contract DSL `{{env}}`, `{{date:%Y%m%d}}`, and `{{var.name}}` verbatim for the Airflow DAG Generator.

## Arrays and paths

The transport must distinguish schema wildcard paths (`silver.tables[*].columns`) from concrete instance paths (`silver.tables[0].columns[2].name`). Canonical alias compilation occurs in Forge; ADCM receives paths already normalized for `CurrentSchemaView` authorization.

## Value precedence

Forge decides only conflicts among Forge rules using explicit priority/specificity. ADCM then applies origin precedence across user, preference, external, enrichment, derived, and default candidates. Forge must not reorder or delete user candidates to enforce its internal rule policy.

## Tests

- **Transport unit:** request/response serialization, timeout/error mapping, malformed responses, auth-reference handling, and revision mismatch.
- **Contract integration:** canonical alias normalization; unknown/ambiguous alias failure; progressive view replacement; defaults activating new requirements; rule priority/scope conflicts; unknown-system generic fallback.
- **Validation/render contract:** `VALID | INVALID | DEFERRED` findings, `DEFERRED_EXTERNAL` final validation, runtime DSL preservation, and separate YAML rendering.
- **Negative:** missing production Forge source/transport blocks the stage; the local UX fixture is not accepted as production authority; provider cannot return ADCM workflow statuses or mutate a draft.
- **Security:** no hidden reasoning or secrets are serialized into boundary payloads.

## Acceptance criteria

- The authoritative Forge owner has supplied and versioned schema/enrichment source and wire protocol; otherwise the stage is explicitly `BLOCKED_INPUT` even though the local UX fixture exists.
- The real adapter passes provider conformance tests without importing schema/rule evaluators into `src/adcm`.
- Alias ambiguity, revision mismatch, deferred dependencies, internal priority, generic fallback, and runtime DSL behavior are tested against the authoritative source.
- ADCM receives complete replacement views and typed candidates/findings; no stateful Forge API exists.
- Final YAML is produced only by Forge's separate render operation.

## Explicit non-goals

Semantic LLM behavior, durable session concurrency, HTTP/UI, and release hardening are deferred. No local fallback enrichment policy may be added to “unblock” this stage.

## Documentation updates

Update `docs/MCP_CONTRACT.md`, `docs/ISSUES_AND_RESOLUTIONS.md`, `docs/DESIGN_DECISIONS.md`, adapter/port architecture docs, and the Stage 3 status in `IMPLEMENTATION_PLAN.md`. Add the owner-provided source reference and revision policy; do not claim fixture ownership for ADCM.

## Completion checklist

- [ ] External source, authoritative bundle, protocol, and revision policy are confirmed.
- [ ] Adapter is stateless and provider-neutral at the port.
- [ ] Canonical path/alias and rule conformance tests pass.
- [ ] Deferred/error/status semantics match the canonical contract.
- [ ] Runtime DSL and schema revision behavior are verified.
- [ ] No ADCM schema/enrichment evaluator or stateful Forge session exists.
