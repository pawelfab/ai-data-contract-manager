# Domain model

## Evidence
A durable record of where information came from. User-origin data points to the user message evidence. MCP candidates may point to rule/enrichment evidence.

## Signal
Schema-agnostic semantic information. It may remain `unbound` until Forge exposes an allowed path with a matching concept. `USER_EXPLICIT` signals require evidence.

## Preference
Cross-cutting user preference that may apply to zero, one or many legal paths over time. User preferences require evidence.

## ValueCandidate
A concrete proposed value for a legal path. It contains origin, evidence, optional Forge rule metadata (`scope`, `rule_id`, explicit priority), source Signal/Preference IDs, revision/sequence and status.

Candidate IDs are unique within `ConversationState`, and optional confidence must be finite.
NaN and positive/negative infinity are invalid candidate state.

Resolution first applies ADCM origin precedence. Forge `priority` resolves conflicts only within
the same origin; corrections then use `created_revision` and `sequence`, with confidence as
the final policy tie-break. A policy-rank collision after confidence is rejected as ambiguous rather
than selecting an input element. UUIDs and input ordering are never business tie-breakers.

Resolution is status-atomic: all IDs, confidence values, and per-path ranks are validated and all
winners are built before any candidate status changes. Any resolution error leaves every input
candidate status unchanged.

## ResolvedValue
The deterministic winner for one path. It intentionally does not duplicate candidate-specific metadata such as `scope`. Use `selected_candidate_id` to inspect provenance.

`ConversationState` validates that every resolved value points to a candidate present at the same
concrete path with `selected` status and canonically identical JSON value, origin, and evidence IDs.
Canonical comparison is type-sensitive (`true`, `1`, and `1.0` differ) while ignoring object-key
order. A dangling or inconsistent selected-candidate reference is invalid aggregate state. Duplicate
candidate IDs and multiple selected candidates for one concrete path are also rejected.

## ContractDraft
The actual nested JSON/YAML-shaped document, not a flat path dictionary. It is a projection of resolved values through the **current** schema view.

Canonical hashing uses strict canonical JSON with sorted keys. Non-finite JSON numbers are rejected.

## ContractPath
Manipulates concrete instance paths such as `silver.tables[0].columns[2].name`. It rejects
malformed paths and schema wildcards such as `[*]`; schema wildcard paths and instance paths
are not the same concept. Nested writes retain `{}` padding for skipped list-of-object elements
and `[]` padding where the next token enters another array. Drafts are dict-backed, so a concrete
path must start with an object key rather than a root-list index.

## CurrentSchemaView
Forge-owned snapshot containing `schema_revision`, current stage and currently legal paths. It replaces the prior view; it is never accumulated by ADCM.

Authorization accepts only a parseable concrete instance path. An `AllowedPath` with `[*]` is a
schema pattern used to authorize matching indexed instances; it cannot itself be projected or
bound as a candidate path.

## Revisions
Business history. Corrections supersede old Signals and candidates but do not delete them.

## Invariants
1. No draft path without current Forge authorization.
2. No ResolvedValue without a selected candidate.
3. No ValueCandidate without origin.
4. USER_EXPLICIT Signal/Candidate requires Evidence.
5. Signal may exist without a path.
6. Preference may affect zero, one or many legal paths.
7. Corrections preserve history.
8. LLM cannot mutate ContractDraft.
9. External MCP cannot mutate ContractDraft.
10. Schema wins over semantic inference.
