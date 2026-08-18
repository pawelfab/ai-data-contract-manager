# Domain model

## Evidence
A durable record of where information came from. User-origin data points to the user message evidence. MCP candidates may point to rule/enrichment evidence.

## Signal
Schema-agnostic semantic information. It may remain `unbound` until Forge exposes an allowed path with a matching concept. `USER_EXPLICIT` signals require evidence.

## Preference
Cross-cutting user preference that may apply to zero, one or many legal paths over time. User preferences require evidence.

## ValueCandidate
A concrete proposed value for a legal path. It contains origin, evidence, optional Forge rule metadata (`scope`, `rule_id`, explicit priority), source Signal/Preference IDs, revision/sequence and status.

## ResolvedValue
The deterministic winner for one path. It intentionally does not duplicate candidate-specific metadata such as `scope`. Use `selected_candidate_id` to inspect provenance.

## ContractDraft
The actual nested JSON/YAML-shaped document, not a flat path dictionary. It is a projection of resolved values through the **current** schema view.

## ContractPath
Manipulates concrete instance paths such as `silver.tables[0].columns[2].name`. Schema wildcard paths and instance paths are not the same concept.

## CurrentSchemaView
Forge-owned snapshot containing `schema_revision`, current stage and currently legal paths. It replaces the prior view; it is never accumulated by ADCM.

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
