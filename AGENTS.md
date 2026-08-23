# ADCM — Mandatory Instructions for Coding Agents

> This file defines the mandatory working procedure for coding agents and LLMs operating in this repository.
> It does not duplicate the full architecture contract. The authoritative architecture rules live in:
>
> `docs/architecture-guardrails.md`

---

## 1. Mandatory reading order

Before planning, implementing, refactoring or reviewing a change, read in this order:

1. `docs/architecture-guardrails.md`
2. `docs/CURRENT_STATE.md`
3. `docs/DECISIONS.md`
4. `docs/architecture.md`
5. `docs/KNOWN_ISSUES.md`
6. service-specific documentation for the service being changed
7. the actual code and tests relevant to the change

Use these sources with the following precedence:

```text
architecture-guardrails.md
    ↓
explicit current task requirements
    ↓
DECISIONS.md
    ↓
CURRENT_STATE.md
    ↓
service-specific docs
    ↓
architecture.md
    ↓
KNOWN_ISSUES.md
    ↓
existing implementation details
```

Important distinction:

- `architecture-guardrails.md` defines mandatory boundaries and design rules;
- `DECISIONS.md` records accepted architectural decisions;
- `CURRENT_STATE.md` describes what is implemented now;
- `architecture.md` explains the system shape and major flows;
- `KNOWN_ISSUES.md` lists known defects/deferred work;
- code and tests are the source of truth for the current implementation, but existing code must not be used to justify violating architectural guardrails.

If code conflicts with `architecture-guardrails.md`, treat the code as technical debt or a defect and report the conflict before extending it.

---

## 2. Core invariant

Preserve this rule after every change:

> **ADCM understands the user. Contract Forge understands the contract.**

If a proposed implementation makes this statement false, stop and redesign.

---

## 3. Non-negotiable service boundaries

### ADCM owns

- conversation and session state;
- chat history;
- evidence and provenance;
- user-value history;
- authority/priority policy;
- PydanticAI semantic interpretation;
- candidate extraction;
- generic deterministic candidate validation;
- fixed-point stabilization;
- optional/agentic context MCP use;
- deciding when user input or a human decision is required;
- user-facing responses;
- YAML rendering.

### Contract Forge owns

- contract loading;
- contract-format parsing;
- `NormalizedContract`;
- JSON Schema semantics;
- `$ref`, `$defs`, `oneOf`, `anyOf` and contract extensions;
- formal schema validation;
- schema requirements/defaults;
- fillable-requirement derivation;
- progressive requirement discovery;
- union/discriminator selection;
- deterministic `x-contract-rules`;
- enrichment resolution;
- discovery presentation metadata;
- Forge validation/domain issues.

### Context MCPs own

- retrieval of external evidence or context;
- deterministic tool-specific operations.

Context MCPs do not mutate `ContractState` directly.

---

## 4. Hard prohibitions

Do NOT:

- import Python runtime classes directly between ADCM and Contract Forge;
- parse `contract.json` in ADCM;
- add `$ref`, `$defs`, `oneOf`, `x-discriminator` or other schema interpretation to ADCM;
- add contract-specific branches such as `if source_type == "jdbc"` to ADCM core/application code;
- add `if system == "sap"` to ADCM core;
- add user-specific `if user_id == ...` branches to core enrichment logic;
- let the LLM mutate `ContractState`;
- let the LLM choose authority/priority;
- let the LLM decide whether mandatory Forge evaluation runs;
- make Contract Forge an optional LLM-selected MCP tool;
- move conversation/session ownership into Forge;
- make ADCM validate JSON Schema directly;
- add environment-specific local/GCP behavior to domain/use-case code;
- solve a local feature by leaking implementation details across service boundaries.

---

## 5. Contract-structure changes

If `contract.json` changes:

1. identify whether only concrete format/layout changed or actual semantics changed;
2. update/add the appropriate `contract_json_vN` adapter;
3. update semantic-path mapping only when a domain anchor moved;
4. extend `NormalizedContract` only if the new semantics cannot be represented;
5. keep ADCM untouched whenever semantics exposed by Forge remain compatible.

If a contract field rename requires ADCM code changes:

> **STOP — architecture boundary leak. Redesign first.**

Concrete contract paths may travel through ADCM as data received from Forge, but ADCM must not hard-code their meaning.

---

## 6. JSON Schema interpretation changes

Changes involving:

- `$ref`;
- `oneOf`;
- `anyOf`;
- discriminator logic;
- `minItems`;
- `x-requirement-expand-items`;
- formal JSON Schema validity;

belong to Forge schema services.

Keep separate:

```text
JsonSchemaValidator
→ formal validity

RequirementEngine
→ formal/fillable requirements

RequirementDiscovery
→ which requirements are visible now
```

Do not use the custom requirement walker as the sole formal validator.

---

## 7. Discovery changes

Change:

- `resources/discovery_rules.json`;
- discovery policy models;
- discovery-policy adapter/service;
- generic discovery selectors/resolvers.

Do not add stage-specific logic to ADCM.

Forbidden:

```python
if stage == "metadata":
    ...
```

Discovery decides visibility/order only.

It must not:

- create values;
- mutate state;
- perform business validation;
- duplicate schema semantics.

---

## 8. Enrichment changes

Rules belong in enrichment data.

Storage belongs behind:

```text
EnrichmentRepositoryPort
```

Runtime applicability belongs in:

```text
EnrichmentResolver
```

Repository adapters may use context to retrieve candidate rules efficiently, but must not decide final applicability.

Prefer declarative rules such as:

```text
{/json/pointer}
valueFrom
pathPattern
generic activation conditions
```

over duplicated per-system code when behavior is truly global.

Examples of global behavior:

```text
sourceSystemGcpId → metadata.id
sourceSystemGcpId → source.systemZrodlowy
enable silver
enable gold
```

Examples of system behavior:

```text
SAP → enable converter
SAP → enable preparator
SAP → system-specific dataset/default
```

Optional branches must be activatable by enrichment even when they are not yet present in the document or current requirements, as long as the target is valid/reachable under the contract.

Derived values must be recomputed so stale system-specific values disappear after relevant user changes.

---

## 9. Source-system invariant

Never confuse:

```text
source system
→ SAP / Rocket / CODAS / ...

technical source type
→ jdbc / json / txt / fixed_width
```

The source system may be copied by enrichment into other contract fields.

It must never be used as the technical discriminator unless the contract explicitly defines that semantic.

---

## 10. LLM changes

PydanticAI/LLM may improve:

- natural-language interpretation;
- evidence-to-requirement matching;
- normalization;
- typo interpretation;
- semantic conflict detection;
- question wording;
- optional context tool selection.

Deterministic behavior stays in application/domain code:

- path validation;
- evidence validation;
- type checks;
- allowed-values checks;
- structural safety;
- authority comparison;
- formal contract validation;
- state mutation.

Flow must remain:

```text
Evidence
    ↓
LLM
    ↓
Candidate
    ↓
deterministic validation
    ↓
ContractState
```

---

## 11. Candidate/state invariants

Every candidate must be treated as a proposal, not as state.

Preserve:

- evidence grounding;
- generic path validation;
- generic type validation;
- `allowed_values` validation when provided by Forge;
- container-destruction protection;
- full-document trial build where required;
- authority protection;
- rejected candidates do not mutate state;
- `ACCEPTED` does not imply `changed=True`.

The fixed-point loop must use actual state mutation as its progress signal.

Do not derive loop progress from candidate status alone.

---

## 12. Editing after `valid=True`

`valid=True` is not a terminal workflow state.

Every feature must preserve the ability to:

- edit existing values;
- add array values;
- change the source system;
- trigger recomputation of derived values;
- revalidate the resulting contract.

Do not add logic that permanently bypasses semantic resolution after completion.

---

## 13. Arrays and structural safety

Before changing array behavior, determine whether the collection is:

- structural, where Forge may expand required items;
- atomic/fillable, where ADCM should accept the whole array.

Do not infer `[0]` only because an array is required.

Expansion must follow explicit contract semantics, e.g.:

```text
minItems
+
x-requirement-expand-items
```

Check every change for:

- parent/scalar conflicts;
- container replacement;
- accidental loss of existing children;
- array-root replacement versus element editing.

---

## 14. Warnings

Warnings exposed to the user represent current stable state, not internal execution history.

Do not turn these into user warnings:

- ordinary missing fields;
- rejected internal LLM candidates;
- resolved obvious typos;
- missing sibling fields.

Warnings should represent:

- semantic anomalies;
- conflicting evidence;
- suspicious values;
- user decisions that are genuinely required.

---

## 15. Context MCP changes

A new context MCP should normally require:

- a new adapter/port/tool integration;
- evidence normalization;
- optional PydanticAI tool exposure.

It must NOT require redesigning the fixed-point stabilization algorithm merely because another evidence source exists.

Context MCP output becomes evidence/context, not direct contract mutation.

---

## 16. File upload changes

Current `attachments: list[str]` means inline attachment text.

Future file upload should be implemented through:

```text
inbound upload adapter
    ↓
FileContentExtractorPort
    ↓
EvidenceItem
```

Do not redesign `EvidenceStore`, heuristics or stabilization solely to support upload.

---

## 17. Feature-plan checklist

Every implementation plan MUST state:

### Ownership

- owning service;
- owning port/service/adapter;
- why this component owns the change.

### Expected change surface

- exact files expected to change;
- services/files explicitly expected NOT to change.

### Boundary checks

- whether ADCM remains unaware of contract format;
- whether Forge remains unaware of conversation/session state;
- whether there are any new cross-service imports;
- whether a new context MCP affects stabilization unnecessarily.

### State invariants

- whether user edits after `valid=True` still work;
- whether source-system changes recompute stale derived values;
- whether the change can create a structural parent/scalar conflict;
- whether repeated accepted values can falsely report progress;
- whether hidden/optional branches can be activated correctly and not prematurely.

### Contract/discovery invariants

- whether formal validation remains independent from discovery;
- whether a contract-format change is isolated to Forge;
- whether array expansion is explicitly justified;
- whether union/discriminator handling remains generic.

### Tests

State the unit, integration and architecture-boundary tests that prove the above invariants.

---

## 18. Required response before implementation

Before coding a non-trivial feature, produce a short implementation note containing:

```text
Owning service:
Owning boundary:
Files to change:
Files/services not to change:
Main invariant:
Tests:
Architecture risks:
```

If the requested change conflicts with `docs/architecture-guardrails.md`, do not silently implement it.
Unexpected complexity is a signal to investigate assumptions before adding code. If a simple requirement requires a complex workaround, escalate the inconsistency instead of implementing the workaround.

Report:

1. the conflict;
2. why it violates the architecture;
3. the smallest compliant alternative.

---

## 19. Documentation maintenance

After a material architecture or behavior change, update only the documents whose responsibility actually changed:

- `docs/architecture-guardrails.md` — only for durable architecture rules/invariants;
- `docs/DECISIONS.md` — for accepted architectural decisions;
- `docs/CURRENT_STATE.md` — for current implemented behavior;
- `docs/architecture.md` — for system shape/major flows;
- `docs/KNOWN_ISSUES.md` — when an issue is added, resolved or superseded;
- service-specific docs — for service implementation details.

Do not copy the same rule into all documents.

Avoid documentation drift.

---

## 20. Final rule

When uncertain where logic belongs, apply:

> **ADCM understands the user. Contract Forge understands the contract.**

And prefer the smallest local change that preserves this boundary.
