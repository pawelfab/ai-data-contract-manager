# Migration: v4 guardrails → v5 consolidated runtime

Main additions:

- progressive `RequirementDiscovery` + JSON discovery policy;
- contract semantic paths (`@sourceSystem`);
- strict/non-strict discovery diagnostics;
- structural-parent `fillable_requirements` filter;
- system-enrichment leak fix;
- global enrichment copy/interpolation using `{/json/pointer}`;
- wildcard `pathPattern` targets for later-discovered fields;
- enrichment/default gating to visible discovery paths;
- recomputation of derived values each round;
- deterministic `CandidateDecision` / `CandidateOutcome`;
- authority enforcement;
- scalar-over-container and JSON Pointer structural protection;
- fixed-point idempotence (`changed` separated from accepted status);
- warning snapshot behavior;
- semantic resolver pass for edits after contract completion;
- user-friendly requirement presentation without invented field meanings;
- `PromptedOutput` and OpenAI-compatible base URL support;
- explicit inline-text attachment semantics;
- architecture-boundary test preventing contract-v1 field names in ADCM core;
- exact supplied contract snapshot preserved + documented runtime compatibility repair.
