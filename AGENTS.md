# ADCM — mandatory instructions for coding agents

Before planning or implementing, read:

1. `docs/CURRENT_STATE.md`
2. `docs/DECISIONS.md`
3. `docs/architecture.md`
4. `docs/architecture-guardrails.md`
5. `docs/KNOWN_ISSUES.md`
6. service-specific docs in the service being changed

Then inspect the actual code and tests. Code is the current implementation source of truth; docs define intended boundaries and known constraints.

## Non-negotiable boundaries

- ADCM owns conversation/session/evidence/user-value state, semantic candidate extraction, authority policy, fixed-point orchestration and user response.
- Contract Forge owns contract parsing, formal requirements/defaults/rules, enrichment and progressive requirement discovery.
- No direct Python imports across services.
- ADCM must never contain concrete v1 contract paths such as `sourceSystemGcpId`.
- The LLM never mutates `ContractState`.
- Forge is a mandatory deterministic call, not an optional LLM-selected MCP tool.
- Context MCPs contribute evidence/tool output, not direct contract mutations.

## Extension rules

### Contract structure changes
Change/add only `contract_json_vN` adapter and semantic-path mapping unless actual normalized semantics changed. If a contract field rename requires ADCM edits, stop and redesign.

### Discovery changes
Change `resources/discovery_rules.json` or discovery-policy adapter/service. Do not add `if stage == ...` to ADCM.

### Enrichment changes
Rules belong in enrichment data. Storage changes belong behind `EnrichmentRepositoryPort`. Matching logic belongs to `EnrichmentResolver`; storage adapters must not decide runtime applicability.

### New derived/copy rules
Prefer declarative `{/json/pointer}` templates and `pathPattern` over per-system duplicated code/rules when behavior is truly global.

### LLM changes
Prompts/adapters may improve semantic extraction, normalization, conflict detection and question wording. Deterministic validation/path/type/authority logic stays in application/domain code.

## Feature-plan checklist

Every plan must state:

- owning service;
- owning port/service/adapter;
- exact files expected to change;
- files/services expected NOT to change;
- boundary/invariant tests;
- whether user edits after `valid=True` still work;
- whether source-system changes recompute stale derived values;
- whether the change can create a structural parent/scalar conflict;
- whether hidden discovery branches can be activated prematurely.
