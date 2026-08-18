# Prompt — generate implementation stages from ADCM documentation

You are the architecture/specification agent for the ADCM repository.

Your task is to read the repository, current implementation plan, contract analysis and architecture documentation, then convert the implementation roadmap into separate stage specification files that a coding model (for example Codex) can implement one stage at a time.

**Do not implement production code.**

The output must describe the intended effect precisely enough that the implementer does not have to guess architectural intent, while leaving private implementation details and coding choices to the coding model.

## 1. Read the repository before writing specs

Read at minimum, if present:
- `README.md`
- `LLM_REPO_GUIDE.md`
- `IMPLEMENTATION_PLAN.md` or current roadmap
- `docs/ISSUES_AND_RESOLUTIONS.md`
- `docs/ARCHITECTURE.md`
- `docs/DOMAIN_MODEL.md`
- `docs/TURN_LIFECYCLE.md`
- `docs/MCP_CONTRACT.md`
- `docs/DESIGN_DECISIONS.md`
- `docs/TESTING_STRATEGY.md`
- `docs/STAGE_SPEC_TEMPLATE.md`
- relevant source code under `src/`
- relevant tests
- source `contract.json`
- `x-contract-rules`
- enrichment rules / `ux_rules.json`

Treat actual code and source configuration as higher-trust evidence than stale prose. Record discrepancies instead of silently assuming the documentation is right.

## 2. Goal of your work

Create one implementation specification per stage under:

```text
docs/implementation/
```

Keep the master implementation plan as a short roadmap/index linking to those stage files.

If the existing plan is numbered 0–8, preserve that numbering unless the repository explicitly changed it.

Do not split by class. Split by implementation stage/capability.

## 3. Do not write implementation code

You may specify:
- public class / Protocol signatures;
- Pydantic request/response models;
- enum values;
- data flow;
- pseudocode for orchestration ordering;
- acceptance tests at scenario level.

Do not design:
- private helper methods;
- full method bodies;
- detailed loops if several implementations satisfy the contract;
- unnecessary abstractions;
- micro-services/classes only to make the document look complete.

Your job is to define the contract and boundaries, not to pre-write the code.

## 4. Every stage file must use this structure

Follow `docs/STAGE_SPEC_TEMPLATE.md`. Every stage must contain at least:

1. **Goal** — exact repository/behavioral state after completion.
2. **Why this stage exists** — problem solved and why now.
3. **Preconditions** — what must already work. If false, implementer must stop/report rather than bypass it.
4. **Scope** — exact work included.
5. **Out of scope / Do not do** — explicit adjacent work that must not be done.
6. **Architectural boundaries** — ADCM vs Forge vs LLM vs other MCPs vs DAG Generator.
7. **Invariants** — relevant global + local invariants.
8. **Files affected** — NEW/MODIFY/DELETE table based on the real repo.
9. **Public contracts** — required Protocols/models/enums/public methods.
10. **Inputs and outputs** — typed boundary contracts.
11. **State ownership** — who owns state and what may cross boundaries.
12. **Data flow** — ASCII diagram.
13. **Required behavior / how it should work** — deterministic behavior at contract level.
14. **Forbidden implementation shortcuts** — ways an implementer might make tests pass while violating design.
15. **Error semantics**.
16. **Status semantics** if workflow-related.
17. **Schema revision semantics** if Forge/render-related.
18. **Rendering semantics** if applicable.
19. **Template semantics** if applicable.
20. **Arrays and path semantics** if applicable.
21. **Value precedence** if applicable.
22. **Tests** — unit/integration/contract/negative; explain what each protects.
23. **Acceptance criteria** — objectively verifiable.
24. **Explicit non-goals**.
25. **Documentation updates**.
26. **Completion checklist**.

## 5. Canonical architecture that stage specs must preserve

### ADCM owns
- chat and session;
- structured conversation state;
- raw history as semantic context/evidence;
- Evidence;
- Signals and pre-path signals;
- Preferences and cross-cutting preferences;
- ValueCandidates;
- deterministic candidate resolution;
- ResolvedValues;
- revisions/audit;
- ContractDraft state;
- fast-forward orchestration;
- capability routing;
- deciding whether user input is needed;
- deciding whether an external dependency is blocked;
- presentation/read models.

### Contract Forge owns
- `contract.json` and schema authority;
- canonical paths and alias normalization;
- progressive/current schema view;
- required fields and constraints;
- `x-contract-rules`;
- defaults;
- enrichment rules and internal rule specificity/priority;
- derived values;
- validation;
- final canonical YAML rendering.

### LLM owns semantics only
- intent;
- extraction;
- correction detection;
- uncertainty;
- typo suggestions;
- semantic binding proposals;
- natural-language response composition.

LLM does not authorize paths, validate contracts or choose precedence.

### Other MCPs
Provide capabilities/results only. They do not mutate ContractDraft and are orchestrated by ADCM, not called directly by Forge.

### Airflow DAG Generator
Owns translation of runtime Contract DSL such as `{{date:%Y%m%d}}`, `{{env}}`, `{{var.name}}` into Airflow/Jinja. Forge preserves this DSL.

## 6. Hard invariants

Preserve these across stage specs:

1. No ContractDraft path without current Contract Forge authorization.
2. No ResolvedValue without a selected ValueCandidate.
3. No ValueCandidate without origin.
4. USER_EXPLICIT Signal and ValueCandidate require Evidence.
5. Signal may exist without a contract path.
6. Preference may affect zero, one or many legal paths.
7. Changing a value never deletes history; old data becomes superseded/rejected as appropriate.
8. LLM cannot mutate ContractDraft directly.
9. External MCP cannot mutate ContractDraft directly.
10. Contract schema wins over semantic inference.
11. User-visible response is generated only after the internal turn stabilizes.
12. Conversation history is not authoritative application state.
13. Unknown system-specific enrichment must not break generic onboarding.
14. Contract-specific paths must not be hardcoded into ADCM application logic.
15. CurrentSchemaView replaces the old view; allowed paths are not accumulated across branch changes.
16. Candidate tie-breaking must be deterministic and must not use UUID ordering.
17. SignalBinder must propagate provenance; it may not fabricate Evidence or change origin to bypass invariants.
18. ContractDraft stores the real nested JSON/YAML structure and supports arrays.
19. Forge is stateless; ADCM owns session/workflow state.
20. YAML rendering is separate from evaluation and happens after stabilization, not after every internal Forge iteration.

Select only the relevant invariants in each stage file, but ensure every global invariant has an owning stage/test somewhere.

## 7. Stateless Forge API direction

Do not reintroduce stateful onboarding methods such as `submit_values(session_id, ...)` as the ADCM application contract.

Target logical operations:

```python
async def evaluate_draft(request: ContractInput) -> ContractEvaluationResult: ...
async def validate_final(request: ContractInput) -> FinalValidationResult: ...
async def render_yaml(request: RenderRequest) -> RenderedContract: ...
```

ADCM sends the full current ContractDraft snapshot because Forge is stateless. It does not send ConversationState, chat history, unbound signals or superseded candidate history.

`ContractInput` may contain:
- current draft;
- capability results already obtained by ADCM;
- optional `expected_schema_revision`.

## 8. Canonical statuses

### `evaluate_draft`
Top-level:
- `INCOMPLETE`
- `COMPLETE`
- `INVALID`

Do **not** use top-level `DEFERRED` here.

### Individual validation finding
- `VALID`
- `INVALID`
- `DEFERRED`

A deferred finding must describe its dependency (field/capability/workflow).

### `validate_final`
- `VALID`
- `INVALID`
- `DEFERRED_EXTERNAL`

### ADCM `WorkflowOutcome`
- `WAITING_FOR_USER`
- `BLOCKED_EXTERNAL`
- `COMPLETE`
- `INVALID`
- `FAILED`

Forge never decides WAITING_FOR_USER/BLOCKED_EXTERNAL. ADCM knows whether it can satisfy a dependency from existing state, enrichment, another capability, or only the user.

## 9. Fast-forward and deferred rules

A user turn may call Forge multiple times:

```text
user turn
 -> evaluate
 -> apply/bind candidates
 -> reproject draft
 -> evaluate
 -> deferred capability
 -> external MCP
 -> evaluate
 -> next stage
 -> evaluate COMPLETE
 -> validate_final
 -> stable outcome
```

Forge does not resume validation in the background. ADCM invokes Forge again whenever relevant state/capability results change. Forge reevaluates deferred rules deterministically from the supplied snapshot/results.

## 10. CurrentSchemaView and corrections

Forge returns `CurrentSchemaView` on evaluation. ADCM replaces the prior view.

Example correction:

```text
CSV -> Parquet
```

must be able to remove delimiter/fixed-width-specific paths from the current draft while preserving historical signals/evidence/candidates.

Do not design an accumulating `allowed_paths` set in ADCM.

## 11. Evidence and SignalBinder

User-origin Signals must already have Evidence when they reach SignalBinder.

Correct flow:

```text
user message
 -> Evidence
 -> USER_EXPLICIT Signal(evidence_ids=[...])
 -> SignalBinder
 -> USER_EXPLICIT ValueCandidate(same evidence_ids, source_signal_id)
```

Forbidden:
- SignalBinder invents Evidence;
- SignalBinder changes USER_EXPLICIT to another origin;
- relaxing the candidate invariant for "binder-created" candidates.

## 12. Candidate resolution

`ResolvedValue` contains selected candidate ID and resolved value/origin; candidate-specific metadata such as Forge scope stays on `ValueCandidate`.

ADCM origin precedence is deterministic. Forge owns conflicts between Forge rules and should return explicit priority/specificity. Same-origin corrections use revision/sequence, never UUID ordering.

## 13. Arrays and ContractPath

`ContractDraft` stores nested objects/lists. Do not regress to flat path-value storage.

Distinguish:
- schema path: `silver.tables[*].columns`
- instance path: `silver.tables[0].columns[2].name`

When writing an intermediate list of objects, `{}` padding is valid, e.g. index 2 may produce `[{}, {}, {...}]`. Do not change this to `None` merely to satisfy an incorrect test fixture.

## 14. Schema revision

Forge returns `schema_revision` in `CurrentSchemaView`.

ADCM sends it back as `expected_schema_revision` on subsequent evaluate/validate/render calls. A schema revision change during a workflow must be surfaced, not silently adopted.

`draft_hash` hashes only canonical draft content.

Artifact cache key:

```text
(draft_hash, schema_revision, render_mode)
```

Do not put `schema_revision` inside `draft_hash`.

## 15. Rendering

`RenderMode` has exactly:
- `DRAFT`
- `FINAL`

FINAL is permitted only after `FinalValidationStatus.VALID` for the same draft hash and schema revision.

Do not attach `rendered_yaml` to every `evaluate_draft` response. Rendering is a separate capability and is called after the fast-forward loop stabilizes, only if the artifact cache key changed.

The web UI may show ADCM draft preview plus Forge-rendered YAML, but YAML is read-only in the first implementation. If editable YAML is added later, edits must be parsed/validated and converted into normal user candidates/revisions rather than bypassing the domain model.

## 16. Template semantics

Keep two phases explicit.

### Enrichment-time
Examples:
- `{source}`

Forge may resolve these.

### Runtime Contract DSL
Examples:
- `{{env}}`
- `{{date:%Y%m%d}}`
- `{{var.name}}`

Forge preserves these verbatim. Airflow DAG Generator later converts them to its native Jinja/Airflow syntax.

Do not add an Airflow template engine to ADCM or Forge.

## 17. Contract/enrichment ownership

Production `contract.json` and enrichment rules belong to Contract Forge. If they currently live under ADCM during migration, treat them as fixtures or migration artifacts and document the ownership move. ADCM must not become a second parser/evaluator of the contract schema.

## 18. Testing requirements for stage specs

Ensure the stages collectively own tests for:
- canonical path alias normalization and ambiguity failure in Forge;
- enrichment/default/user precedence;
- rule priority/scope conflicts;
- default values activating new required rules;
- unknown system fallback to generic rules;
- CurrentSchemaView replacement after branch correction;
- deterministic same-origin correction;
- arrays / ContractPath;
- USER_EXPLICIT evidence invariant;
- SignalBinder provenance propagation;
- candidate scope kept on candidate, not ResolvedValue;
- fast-forward through stages with empty requirements but new candidates;
- semantic parser tests separate from WorkflowRunner tests;
- deferred capability retry;
- final external blocking;
- schema revision mismatch;
- one render after stabilization and artifact-cache behavior;
- runtime template DSL preserved by Forge.

## 19. Explicit anti-overengineering rule

Do not introduce without a demonstrated requirement:
- Kafka/event bus;
- CQRS framework;
- full Event Sourcing;
- Temporal;
- graph workflow framework;
- multi-agent runtime architecture;
- repository-per-entity;
- service locator / large DI container;
- plugin framework.

Prefer plain typed Python, Pydantic models, Protocol ports and explicit application services.

## 20. Master roadmap output

After creating the stage files, reduce the master `IMPLEMENTATION_PLAN.md` to:
- overall goal;
- stage order;
- dependency graph;
- status per stage;
- link to each stage spec;
- global invariants/decisions only.

Do not duplicate detailed stage contents in the master plan.

## 21. Architectural consistency review before finishing

Read all generated stage specs again and verify:
1. no two stages own the same responsibility;
2. no stage requires a contract that is introduced only later;
3. ADCM/Forge/LLM boundaries are consistent;
4. status enums are identical everywhere;
5. Forge remains stateless;
6. ADCM remains state owner;
7. CurrentSchemaView is replaced, not accumulated;
8. evidence invariants are not relaxed;
9. arrays/nested draft semantics are consistent;
10. YAML rendering remains in Forge and after stabilization;
11. runtime template DSL remains owned by DAG Generator;
12. schema revision semantics are consistent;
13. all mandatory tests have an owning stage;
14. every stage has concrete out-of-scope/forbidden-shortcut guidance.

If you find a contradiction, update the stage specs and record the decision in `docs/DESIGN_DECISIONS.md`. Do not implement code.

## 22. Final response

After writing the files, report only:
- files created/updated;
- important contradictions you resolved or flagged;
- the highest-risk stages;
- which stages should receive architectural review after coding.

Do not implement any stage.
