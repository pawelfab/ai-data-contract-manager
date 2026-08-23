# ADCM Architecture Guardrails

> **Status:** authoritative architecture contract for the whole repository  
> **Scope:** ADCM, Contract Forge, future MCP services, shared integration rules  
> **Audience:** developers, reviewers and LLM coding agents  
> **Priority:** this document takes precedence over feature plans, local implementation notes and ad-hoc refactor proposals when they conflict with architectural boundaries.

---

## 1. Purpose

This document defines the architectural rules of ADCM.

The goal is not to freeze the design. The goal is to keep change local:

> **A feature should modify the smallest responsible component and must not leak implementation details across service boundaries.**

The system should remain:

- deterministic where ordinary code can guarantee correctness,
- semantic/agentic only where interpretation is genuinely required,
- modular,
- independently testable,
- resilient to LLM mistakes,
- easy to evolve without propagating changes across unrelated services.

Before planning or implementing any change, read this document first.

---

# 2. Core architectural principle

## Isolate reasons to change

A component that changes for one reason must not force unrelated parts of the system to change.

Examples:

- a new `contract.json` structure is a Contract Forge adapter concern, not an ADCM concern;
- a new enrichment storage backend is an `EnrichmentRepositoryPort` adapter concern;
- a new LLM provider is an ADCM outbound-adapter concern;
- a new context MCP such as Atlassian, Repository, Schema Explorer or Visualizer must not be added to Contract Forge;
- a deployment-specific logging destination belongs to logging/bootstrap adapters, not domain or use-case code.

The most important system-wide rule is:

> **ADCM understands the user. Contract Forge understands the contract.**

If that statement becomes false after a change, review the design before implementation continues.

---

# 3. Repository and service structure

The repository is a monorepo, but services are independent runtime units.

```text
repo-root/
├── AGENTS.md
├── docs/
│   ├── architecture-guardrails.md
│   ├── architecture.md
│   ├── service-boundaries.md
│   ├── integration-flow.md
│   └── protocols/
│
├── ai-data-contract-manager/
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── src/adcm/
│   ├── tests/
│   └── docs/
│
└── mcp-servers/
    ├── mcp-contract-forge/
    │   ├── pyproject.toml
    │   ├── Dockerfile
    │   ├── resources/
    │   ├── src/contract_forge/
    │   ├── tests/
    │   └── docs/
    │
    └── future-mcp-services/
```

Each service owns its own:

- `pyproject.toml`,
- local `.venv`,
- dependencies,
- tests,
- version,
- Dockerfile,
- runtime configuration,
- documentation.

Do not create a shared runtime package only to make cross-service Python imports convenient.

---

# 4. Service boundaries are mandatory

## 4.1 AI Data Contract Manager (ADCM)

ADCM owns:

- user sessions;
- chat history;
- `EvidenceStore`;
- provenance;
- `ContractState`;
- user-value history;
- authority/priority resolution;
- PydanticAI semantic interpretation;
- optional context MCP tools;
- deterministic stabilization loop;
- candidate validation;
- deciding when human input is required;
- question generation;
- final conversation responses;
- YAML rendering.

ADCM must NOT:

- parse `contract.json`;
- understand `$defs`, `$ref`, `oneOf`, `anyOf`, `x-contract-rules`, `x-contract-rules-spec`, `x-discriminator` or other contract-format details;
- implement Contract Forge validation rules;
- know enrichment persistence format;
- hard-code source-system dictionaries instead of using contract/enrichment semantics;
- let the LLM mutate `ContractState` directly;
- let the LLM decide whether mandatory Forge evaluation should run.

Examples of forbidden ADCM logic:

```python
if path == "/metadata/sourceSystemGcpId":
    ...

if source_type == "jdbc":
    ...

if "JdbcSourceConfig" in schema:
    ...
```

ADCM may receive paths and values from Forge as **data**, but must not interpret contract-specific semantics in core/application logic.

---

## 4.2 MCP Contract Forge

Contract Forge is a deterministic domain service.

Forge owns:

- loading raw contract sources;
- parsing the current contract format;
- translating raw contract files to `NormalizedContract`;
- schema semantics;
- formal JSON Schema validation;
- requirement discovery;
- defaults;
- deterministic `x-contract-rules`;
- `oneOf` / discriminator branch selection;
- enrichment resolution;
- discovery policy;
- presentation metadata for requirements;
- Forge issues;
- stable Forge API responses.

Forge must NOT:

- own conversations;
- maintain chat history;
- use an LLM to guess contract values;
- import ADCM runtime code;
- expose raw contract-format implementation details for ADCM to interpret;
- run the ADCM stabilization loop internally.

Forge should remain deterministic and normally should not need PydanticAI.

---

## 4.3 Other MCP services

Future MCP services may include:

- Atlassian MCP;
- Schema Explorer;
- Repository Context MCP;
- Visualizer MCP;
- other context/data services.

These services should normally return raw or structured evidence/context.

Central semantic interpretation remains in ADCM unless an MCP truly has an independent semantic task that justifies its own LLM.

Do not add an LLM to every MCP by default.

---

# 5. Mandatory vs agentic MCP split

Contract Forge is a mandatory deterministic dependency:

```text
ADCM stabilization loop
    ↓
ContractForgePort
    ↓
MCP adapter
    ↓
Contract Forge
```

Contract Forge is NOT placed in the PydanticAI agent's free tool-choice set.

Context MCPs are optional/agentic tools:

```text
PydanticAI
    ↓
Atlassian / Repository / Schema Explorer / Visualizer / future context MCPs
```

The agent may choose context tools, but ADCM remains responsible for:

- evidence registration;
- provenance;
- authority;
- candidate acceptance;
- state changes.

---

# 6. Cross-service communication

ADCM and Forge communicate only through a protocol boundary.

```text
ADCM
   ↓
ContractForgePort
   ↓
ForgeMcpAdapter
   ↓ MCP / DTO
Contract Forge
```

Direct Python imports between runtime services are forbidden.

Do not do this in ADCM:

```python
from contract_forge.domain.models import Requirement
```

ADCM may maintain local DTOs matching the wire protocol.

A shared protocol package should be introduced only if real DTO drift becomes a proven maintenance problem.

---

# 7. Ports & Adapters

Create ports only at real I/O or change boundaries.

Examples:

## Forge

- `ContractSourcePort`
- `ContractParserPort`
- `EnrichmentRepositoryPort`
- `DiscoveryPolicyRepositoryPort`

## ADCM

- `ContractForgePort`
- `HeuristicsPort`
- `SessionRepositoryPort`
- `ApplicationLoggerPort`
- `SessionLoggerPort`
- future context MCP ports
- future `FileContentExtractorPort`

Do not create a port for every internal helper or deterministic service.

Internal deterministic logic may use ordinary classes/functions.

---

# 8. Contract format isolation

`contract.json` is an implementation detail of Forge.

ADCM must never parse or understand it.

Expected flow:

```text
contract.json
   ↓
ContractSourcePort
   ↓
ContractParserPort
   ↓
contract_json_v1 adapter
   ↓
NormalizedContract
   ↓
RequirementEngine / RuleEngine / Discovery / Enrichment / Validation
```

Only the concrete format adapter may know details such as:

- `$defs`;
- `$ref`;
- `required`;
- `default`;
- `oneOf`;
- `anyOf`;
- `x-contract-rules`;
- `x-contract-rules-spec`;
- `x-discriminator`;
- `x-requirement-expand-items`.

When contract structure changes:

1. modify the existing format adapter or add a new adapter, e.g. `contract_json_v2`;
2. map the new format into the normalized domain model;
3. extend the normalized model only if the semantics changed;
4. keep Forge use cases, ADCM and the wire protocol unchanged whenever semantics remain compatible.

### Stop condition

If a contract-format change requires edits in ADCM:

> **STOP. The architecture boundary is leaking. Redesign before continuing.**

---

# 9. Semantic paths

Forge may need stable domain concepts independent of concrete JSON Pointer locations.

Example:

```text
source system
```

may map in `contract_json_v1` to:

```text
/metadata/sourceSystemGcpId
```

through:

```python
ContractSemanticPaths(
    source_system="/metadata/sourceSystemGcpId"
)
```

Semantic paths:

- belong to the contract-format adapter;
- may be consumed by Forge services such as discovery and enrichment context;
- must not be hard-coded in ADCM;
- should be used only for important domain anchors.

Do not map every contract field. That would create a second schema.

---

# 10. Three separate concepts: validation, requirements, discovery

These must remain separate.

## 10.1 Formal validation

Question:

> Is the current document formally valid?

Authority:

```text
JsonSchemaValidator
+
RuleEngine
```

The full JSON Schema validator is the formal schema authority.

Custom walkers must not determine final validity on their own.

Conceptually:

```python
valid = not schema_errors and not rule_errors
```

`valid=True` means only that the current document satisfies formal rules.

It does NOT mean the session is closed.

---

## 10.2 Formal / fillable requirements

Question:

> Which values are structurally missing and can actually be supplied?

Not every schema `required` node should be shown to the user.

Example:

```text
/metadata
/metadata/id
/metadata/version
```

`/metadata` is a structural container.

ADCM should receive fillable requirements such as:

```text
/metadata/id
/metadata/version
```

not the container itself.

---

## 10.3 Requirement discovery

Question:

> Which fillable requirements should ADCM expose now?

Flow:

```text
formal requirements
    ↓
fillable filtering
    ↓
RequirementDiscovery
    ↓
visible requirements
```

Discovery is UX/workflow policy, not schema validation.

ADCM must not contain stage logic.

Forbidden:

```python
if stage == "metadata":
    ...
```

---

# 11. Discovery policy

Current adapter:

```text
JsonDiscoveryPolicyRepository
→ resources/discovery_rules.json
```

Discovery policy may contain concepts such as:

- `whenMissing`;
- `whenPresent`;
- `whenAnyMissing`;
- `expose`;
- `exposeMatchingSchemaRequirements`;
- future `exposePrefixes` or equivalent generic selectors.

Semantic tokens such as:

```text
@sourceSystem
```

are resolved through `SemanticPathResolver`.

Discovery must:

- never create values;
- never mutate the document;
- never validate business values;
- never invent requirements;
- only decide what currently discovered requirements are visible.

Invalid discovery configuration should be detectable.

Recommended behavior:

- strict/dev mode → fail fast;
- production → controlled warning / safe fallback.

---

# 12. Arrays and controlled expansion

Forge must not invent array element `[0]` without explicit schema semantics.

Validation cardinality and requirement discovery are separate.

Use:

```text
minItems
→ formal cardinality constraint

x-requirement-expand-items
→ whether RequirementEngine may synthesize missing item indexes
```

Example structural collection:

```json
"tables": {
  "type": "array",
  "minItems": 1,
  "x-requirement-expand-items": true
}
```

This may produce:

```text
/silver/tables/0/...
```

Data collections such as `columns` should normally remain atomic/fillable as a whole:

```text
/silver/tables/0/columns
```

even when they have:

```json
"minItems": 1
```

This lets ADCM accept a whole list of columns in one candidate instead of asking for `columns[0].name`, `columns[0].type`, etc.

General rule:

```text
Object:
  required child → recurse

Array:
  existing elements → recurse
  missing elements → synthesize only when explicitly enabled by schema metadata

Optional branch:
  do not synthesize unless activated by schema/rule/enrichment
```

---

# 13. `oneOf` and union branch selection

`oneOf` must not be treated as the union of all branch requirements.

For discriminated unions, use a generic contract extension:

```json
"x-discriminator": {
  "path": "sourceType"
}
```

Forge must use a generic `UnionBranchSelector`.

It must not know domain-specific values such as JDBC/SAP in implementation code.

### Missing discriminator

Return only the discriminator requirement and its allowed values.

Example:

```text
/source/sourceType
allowed_values = [jdbc, json, txt, fixed_width]
```

Do not expose all requirements from all branches.

### Selected discriminator

Recurse only into the selected branch.

### Invalid discriminator

Return a validation issue on the discriminator path.

### Ambiguous discriminator

Treat as a contract-definition error.

In strict/dev mode, fail fast.

No special-case code such as:

```python
if source_type == "jdbc":
```

belongs in generic schema services.

---

# 14. Formal JSON Schema validation

RequirementEngine is not a replacement for a complete JSON Schema validator.

Forge should keep these responsibilities separate:

```text
contract.json
   ├── RequirementEngine
   │      → requirements
   │
   └── JsonSchemaValidator
          → formal schema validity/errors
```

Use the raw schema with an appropriate standard validator, e.g. Draft 2020-12 when that is the supported contract dialect.

User-facing issues may be mapped/filtered separately from formal validity.

A dedicated issue mapper is preferred over mixing presentation policy into the validator.

Missing future fields normally belong in requirements/questions, not noisy user-facing warnings.

---

# 15. Enrichment ownership

Enrichment belongs only to Forge.

```text
ux_rules.json
    ↓
EnrichmentRepositoryPort
    ↓
EnrichmentResolver
    ↓
Forge suggestions
```

ADCM must not implement enrichment rules.

---

# 16. Enrichment categories

Conceptual authority categories include:

```text
USER_DIRECT
> USER_REFERENCED
> USER_ENRICHMENT
> SYSTEM_ENRICHMENT
> GLOBAL_ENRICHMENT
> DEFAULT
```

The exact ranking is application policy and should exist in one place.

Observed conventions from Repository/Schema Explorer are evidence/advisory context and must not silently override stronger sources.

---

# 17. Global enrichment

Global enrichment applies independently of a specific source system.

Examples:

```text
sourceSystemGcpId
→ metadata.id

sourceSystemGcpId
→ source.systemZrodlowy

enable silver
enable gold
```

When behavior is identical for all systems, use one global rule rather than duplicating one rule per source system.

---

# 18. System enrichment

System enrichment applies only when the current `EnrichmentContext.source_system` matches the rule.

Examples:

```text
SAP
→ silver dataset

SAP
→ enable converter

SAP
→ enable preparator
```

System enrichment must not activate when source system is unknown.

The repository may use context to efficiently retrieve candidate rules, but the final applicability decision belongs to `EnrichmentResolver`.

---

# 19. Dynamic enrichment / templating

Enrichment may derive a target value from another field.

Example:

```json
{
  "path": "/metadata/id",
  "value": "{/metadata/sourceSystemGcpId}"
}
```

or an equivalent normalized `valueFrom`.

Do not create repetitive rules such as:

```text
SAP → metadata.id = SAP
Rocket → metadata.id = Rocket
ABC → metadata.id = ABC
```

if the relationship is globally identical.

---

# 20. Activation of optional branches

The JSON Schema may keep components such as:

```text
silver
gold
converter
preparator
```

optional.

Business defaults/policies may activate them through enrichment:

```text
GLOBAL
→ silver.enabled = true
→ gold.enabled = true

SYSTEM: SAP
→ converter.enabled = true
→ preparator.enabled = true
```

Forge must allow enrichment to activate a schema-valid optional branch.

An enrichment target must not be rejected only because:

- the target does not yet exist in the document;
- the target is not a currently missing requirement.

Otherwise optional branches could never be activated.

At the same time, enrichment must only create paths that are valid/reachable under the normalized contract.

---

# 21. Derived values are recomputable

Derived values are not permanent truth.

Example:

```text
system = SAP
→ dataset = silver_sap
```

If the user changes:

```text
SAP → Rocket
```

old SAP-derived values must disappear.

Derived state must therefore be recomputed from current state/context rather than only appended forever.

User-entered values and derived values should remain logically separate.

---

# 22. Source system vs source type

This is a critical invariant.

Example domain value:

```text
metadata.sourceSystemGcpId
→ SAP / Rocket / CODAS / ...
```

Technical source type:

```text
source.sourceType
→ jdbc / json / txt / fixed_width
```

These concepts are not interchangeable.

Never map:

```text
SAP → source.sourceType
```

A source system may be copied through enrichment to:

```text
metadata.id
source.systemZrodlowy
```

but the technical source type is a separate value/discriminator.

---

# 23. Evidence and conversation

Conversation history and evidence are separate concerns.

## Conversation

Raw user/assistant messages.

## EvidenceStore

Trusted source records used to justify candidates:

- user text;
- attachment text;
- Jira;
- repository;
- Schema Explorer;
- other context MCPs.

An LLM-derived candidate must reference valid `evidence_id`.

ADCM derives authority/provenance from the stored evidence source rather than trusting values invented by the LLM.

---

# 24. Attachments

Current API behavior:

```text
attachments: list[str]
```

means inline attachment text.

Each item is stored as separate evidence.

Do not interpret it as:

- path;
- upload ID;
- URL.

Future file upload should be introduced through an inbound boundary:

```text
FastAPI upload
    ↓
FileContentExtractorPort
    ↓
EvidenceItem
```

without changing ContractState, stabilization or heuristic semantics.

---

# 25. LLM responsibilities

Use PydanticAI/LLM for non-deterministic semantic work:

- intent interpretation;
- matching evidence to current requirements;
- interpreting Jira/wiki/text attachments;
- detecting semantic conflicts;
- typo interpretation;
- choosing optional context tools;
- composing questions;
- unambiguous normalization.

Example:

```text
"every day at 7am"
→ "0 7 * * *"
```

when the target contract field clearly expects cron.

---

# 26. LLM restrictions

Do NOT use LLMs for work ordinary code can guarantee.

LLM must not:

- validate the contract formally;
- choose authority;
- persist state;
- mutate `ContractState`;
- decide whether mandatory Forge evaluation runs;
- replace deterministic rule engines;
- create arbitrary canonical contract paths;
- silently resolve meaningful conflicts.

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

# 27. Candidate decisions

Candidate is a proposal, not state.

Suggested statuses:

```text
ACCEPTED
SHADOWED
REJECTED
NEEDS_USER_DECISION
```

Possible rejection reasons include:

```text
unknown_evidence
low_confidence
unknown_path
invalid_type
value_not_allowed
structural_conflict
destroys_container
```

Rejected candidate:

- does not enter ContractState;
- does not remove evidence;
- normally does not create a user-facing warning.

Candidate logs may later be stored by `SessionLogger`.

---

# 28. Generic candidate validation

ADCM may validate metadata supplied by Forge generically.

Example:

```text
Requirement.allowed_values
```

allows:

```python
candidate.value in requirement.allowed_values
```

without knowing what the path means.

ADCM must not add contract-specific validation such as:

```python
if path == "/source/sourceType":
    ...
```

---

# 29. Container safety

A candidate must not silently destroy existing structure.

Example:

```text
/table/project = abc
```

followed by:

```text
/table = "abc"
```

must not erase the object.

Use deterministic protection such as:

```text
destroys_container
→ REJECTED
```

`set_pointer()` is the last defensive boundary and should raise a controlled `JsonPointerError` on incompatible traversal.

Do not silently convert scalars to `{}` or overwrite containers to “repair” the structure.

---

# 30. Fixed-point stabilization

ADCM owns stabilization.

```text
Forge.evaluate(document)
    ↓
requirements + suggestions
    ↓
search evidence
    ↓
LLM candidates
    ↓
deterministic application
    ↓
state actually changed?
    ├── yes → evaluate again
    └── no  → fixed point
```

Forge must not internally run:

```text
apply suggestion
→ evaluate
→ apply suggestion
→ ...
```

That would duplicate the orchestrator responsibility.

---

# 31. `changed` is not the same as `accepted`

A candidate can be valid but equal to the current value:

```text
status = ACCEPTED
changed = false
```

Stabilization progress must be based on actual state mutation.

Do not calculate:

```python
changed = any(decision.status == ACCEPTED)
```

This can create infinite loops.

---

# 32. Editing after completion

`valid=True` does not lock a session.

Users may edit any existing value after the document becomes formally valid.

Example:

```text
change version to 2.0.0
```

must still be processed.

Completeness/validity is a property of current state, not a terminal workflow stage.

---

# 33. Warnings

Warnings returned to the user should represent the current fixed point.

Do not accumulate warnings across stabilization rounds as current API state.

Historical warnings belong in audit/session logging.

Do not warn for:

- ordinary missing required fields;
- a missing sibling field;
- an obvious typo that was unambiguously normalized;
- internal rejected candidates.

Warn for:

- contradictory evidence;
- semantic anomalies;
- conflicting sources;
- suspicious values;
- conditions requiring a human decision.

---

# 34. User-friendly requirement presentation

Forge should supply metadata such as:

```text
path
title
description
expected_type
allowed_values
```

Discovery policy may add presentation overrides.

LLM should not invent business meanings.

Prefer:

```text
Data File ID (/metadata/dataFileId)
```

over:

```text
input filename ID
```

unless the contract description explicitly supports that meaning.

---

# 35. Runtime configuration files

Forge currently uses three conceptually different configuration sources.

## `contract.json`

Formal contract semantics:

- JSON Schema;
- `$defs`;
- `$ref`;
- required;
- type;
- enum;
- const;
- defaults;
- `oneOf`;
- `anyOf`;
- `x-contract-rules`;
- `x-discriminator`;
- `x-requirement-expand-items`.

## `ux_rules.json`

Enrichment policy:

- global rules;
- system rules;
- future user rules;
- copied/templated values;
- component activation.

## `discovery_rules.json`

Requirement visibility/order and presentation.

Do not mix their responsibilities.

---

# 36. `contract.input.json`

`contract.input.json` is not a runtime source of truth.

It was only useful as a historical copy during an earlier contract repair.

If `contract.json` is now authoritative:

- Forge should read only `contract.json`;
- remove `contract.input.json` from runtime resources, or archive it outside runtime resources.

Avoid two similar contract files that future developers/LLMs may confuse.

---

# 37. Pydantic vs PydanticAI

Use Pydantic for:

- models;
- DTO;
- validation;
- settings;
- serialization.

Use PydanticAI for:

- semantic agent behavior;
- model/provider abstraction;
- structured semantic output;
- context tool use.

PydanticAI primarily belongs to ADCM.

---

# 38. Local LLM compatibility

Provider limitations must remain in the outbound LLM adapter.

For OpenAI-compatible endpoints without tools, ADCM may use:

```python
PromptedOutput(...)
```

instead of tool-based structured output.

Do not modify domain architecture to accommodate one provider.

---

# 39. Resource paths and settings

Paths to:

```text
.env
resources/
```

must resolve relative to the service/package root, not accidental process `cwd`.

The same code should behave consistently under:

```text
uv run
python -m
Docker
Cloud Run
```

---

# 40. Logging

Keep application logging and session audit separate.

## Application logs

```text
ApplicationLoggerPort
local → stdout/file
GCP → stdout / Cloud Logging
```

## Session audit

```text
SessionLoggerPort
local → JSONL
GCP → BigQuery
```

Do not merge logging with `SessionRepository`.

---

# 41. Architecture tests

Maintain executable architecture guardrails where useful.

Examples:

- ADCM domain/application must not import `contract_forge`;
- Forge must not import `adcm`;
- ADCM must not contain contract-model branches such as `if sourceType == "jdbc"`;
- generic DTO paths received from Forge are allowed as data.

Do not write naive substring tests that reject legitimate data strings everywhere.

Test dependency violations and hard-coded business logic, not accidental text occurrence.

---

# 42. Change strategy

Prefer small vertical changes:

```text
small contract/interface
    ↓
implementation in one responsible component
    ↓
unit tests
    ↓
adapter/integration test
    ↓
connect next component
```

Do not implement abstractions for hypothetical future requirements.

Do preserve known invariants:

- arbitrary JSON Pointer editing;
- full provenance;
- authority rules;
- revalidation;
- independent services;
- editable state after `valid=True`;
- deterministic contract interpretation.

---

# 43. Feature planning checklist

Before implementing any feature, answer:

1. What is the primary reason this change exists?
2. Which service owns that responsibility?
3. Which existing port/adapter is the correct boundary?
4. If no port exists, is a new boundary truly justified?
5. Which files should change?
6. Which services/files should explicitly NOT change?
7. What unit/integration/architecture test proves the boundary still holds?
8. If contract format or enrichment storage changes, can ADCM remain untouched?

If the answer to 8 is no, review the design before implementation.

---

# 44. Ownership map

```text
contract.json structure changes
→ Forge contract adapter

JSON Schema interpretation changes
→ Forge schema services

oneOf/discriminator changes
→ Forge UnionBranchSelector / schema engine

formal schema validation changes
→ Forge JsonSchemaValidator

question order / progressive discovery
→ discovery_rules.json / discovery services

enrichment rule changes
→ ux_rules.json

enrichment storage changes
→ EnrichmentRepository adapter

conversation semantics
→ ADCM heuristics/message handling

LLM provider changes
→ ADCM outbound LLM adapter

MCP transport changes
→ corresponding MCP adapter

session persistence changes
→ SessionRepository adapter

logging destination changes
→ logging adapters/bootstrap
```

---

# 45. Anti-patterns / stop conditions

Stop and review architecture before merging if any of these appears.

### A. Contract parsing in ADCM

Forbidden.

### B. Python imports between ADCM and Forge

Forbidden.

### C. `if source == "sap"` in ADCM core

Forbidden.

### D. `if user_id == ...` in core enrichment logic

Forbidden.

### E. LLM directly mutates ContractState

Forbidden.

### F. Contract format field rename requires changes across ADCM

Boundary leak.

### G. New context MCP requires stabilization-loop redesign

Likely boundary leak.

### H. Forge begins managing conversation state

Forbidden.

### I. ADCM begins validating JSON Schema directly

Forbidden.

### J. Enrichment storage query appears inside EnrichmentResolver

Storage/domain responsibility leak.

### K. Large orchestrator accumulates logic owned by ports/adapters/domain services

Review and split responsibilities.

### L. Deployment-specific local/GCP branches appear inside domain/use-case code

Infrastructure leak.

---

# 46. Complexity escalation and assumption checking

Unexpected implementation complexity is a signal to re-check assumptions before adding code.

Before introducing a workaround, special-case logic, compatibility layer, complex transformation, or substantial additional code, verify whether the complexity is caused by:

* an incorrect or inconsistent input, contract, schema, configuration, or existing implementation;
* an ambiguous, incomplete, or overly literal interpretation of the requirement;
* a constraint that was assumed to be absolute but conflicts with the intended behavior;
* an architectural boundary being used to compensate for a defect in another component;
* a requirement whose implementation cost is disproportionate to the expected business behavior.

A requirement such as:

```text
do not modify contract.json
```

must not be interpreted as:

```text
compensate for any defect in contract.json with arbitrarily complex application code
```

Constraints define the expected solution space, but they do not make inconsistent inputs or assumptions correct.

## Mandatory stop condition

If a seemingly simple requirement starts requiring:

* significant workaround logic;
* many special cases;
* duplicated logic;
* complex state reconciliation;
* non-obvious transformations;
* changes across multiple unrelated components;
* substantially more code than the requirement appears to justify;

**STOP before implementing that complexity.**

First determine whether the implementation difficulty exposes a problem in the requirement, contract, schema, configuration, architecture, or assumptions.

Report briefly:

1. **Observed problem** — what does not behave as expected.
2. **Likely cause** — which assumption, input, constraint, or existing design causes it.
3. **Workaround cost** — what additional complexity would be required to preserve the current assumptions.
4. **Simpler alternative** — what change or clarification would remove that complexity.
5. **Recommendation** — whether to continue with the workaround or correct the underlying cause.

Do not hide an upstream defect behind downstream complexity.

Prefer:

```text
The contract definition is inconsistent with the requested behavior.
Correcting the contract requires a small change.
Keeping the contract unchanged would require a complex parser workaround.
Recommend correcting the contract.
```

over silently implementing the workaround.

## Proportionality rule

Implementation complexity should be proportional to domain complexity.

If a simple domain rule requires a complicated implementation, investigate why before continuing.

Do not assume that complexity is justified merely because the task can technically be implemented.

## Protected files and immutable inputs

Files or components marked as:

```text
do not modify
read-only
out of scope
immutable
```

should normally remain unchanged.

However, if such a component appears incorrect and keeping it unchanged would force disproportionate complexity elsewhere:

1. do not modify it silently;
2. do not silently compensate for it;
3. report the inconsistency;
4. explain the smallest corrective option;
5. wait for the implementation decision if the choice materially changes scope or architecture.

The purpose of an immutability constraint is to control scope, not to conceal defects.

---

# 47. Rule for LLM coding agents

Before planning or implementing a repository change:

1. read this file completely;
2. identify the owning service;
3. identify the relevant boundary;
4. identify files expected to change;
5. identify files/services expected NOT to change;
6. identify tests protecting the boundary;
7. verify that the requested behavior is consistent with the existing inputs, contracts, schemas and configuration;
8. estimate whether the straightforward implementation is proportionate to the requirement.

During implementation continuously apply this rule:

> **Unexpected complexity is a signal to investigate assumptions before adding code.**

If the straightforward solution stops being straightforward:

1. identify why;
2. check whether an input, requirement, schema, configuration or assumption is inconsistent;
3. avoid introducing compensating complexity until the cause is understood.

If a feature request or local implementation plan conflicts with this document:

1. do not silently implement the conflicting design;
2. state the conflict;
3. propose a solution preserving the architectural boundaries.

If a feature request can only be satisfied through a disproportionately complex workaround:

1. do not silently implement the workaround;
2. state the underlying inconsistency or uncertainty;
3. compare the workaround with the smallest corrective alternative;
4. recommend the simpler design unless there is a documented reason to preserve the workaround.

Do not optimize a local implementation at the cost of:

* service-boundary erosion;
* hidden technical debt;
* unnecessary special cases;
* compensating for incorrect upstream definitions;
* implementation complexity that is disproportionate to the domain problem.

The agent is expected to challenge implementation assumptions when evidence in the repository shows they are incorrect.

It must distinguish between:

```text
"This requirement is difficult."
```

and:

```text
"This requirement became difficult because one of our assumptions is probably wrong."
```

The second case must be escalated before substantial complexity is introduced.


---

# 48. Final mental model

```text
                         ┌─────────────────────┐
                         │        USER         │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │        ADCM         │
                         │ conversation        │
                         │ evidence            │
                         │ ContractState       │
                         │ stabilization       │
                         │ PydanticAI          │
                         └──────────┬──────────┘
                                    │ MCP
                                    ▼
                         ┌─────────────────────┐
                         │   CONTRACT FORGE    │
                         │ contract parsing    │
                         │ schema semantics    │
                         │ discovery           │
                         │ enrichment          │
                         │ validation          │
                         └─────────────────────┘
                                    │
                  ┌─────────────────┼─────────────────┐
                  │                 │                 │
                  ▼                 ▼                 ▼
              Atlassian        Schema Explorer      Repo MCP
              evidence          context/evidence    evidence
```

The architectural invariant to preserve after every change is:

> **ADCM understands the user. Contract Forge understands the contract.**
