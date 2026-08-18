# LLM repository guide — ADCM

## Mission

This repository implements ADCM: the chat/session/orchestration layer that sits between a user/LLM and MCP servers used to build a contract.

When modifying this repo, preserve these rules before optimizing anything else.

## Non-negotiable invariants

1. Contract Forge schema is authoritative. Never infer or persist a contract path that Contract Forge did not authorize.
2. LLM cannot mutate `ContractDraft` directly.
3. External MCP output cannot mutate `ContractDraft` directly.
4. `Signal` is schema-agnostic and may exist before any contract path exists.
5. `Preference` is cross-cutting and may eventually produce zero, one or many candidates.
6. Every `ValueCandidate` has an origin.
7. User-origin candidates reference evidence from a user message.
8. `ResolvedValue` is selected from candidates by deterministic policy, not by LLM preference.
9. Historical values are superseded, not deleted. Revision/audit history is append-only conceptually.
10. Draft projection accepts only resolved values whose paths are in the current authoritative allowed-path set.

## Responsibility map

### LLM / semantic interpreter
Allowed:
- recognize intent;
- extract concepts/signals from natural language;
- detect likely corrections or confirmations;
- detect likely typos and suggest canonical values;
- propose semantic bindings from a signal to one of MCP-provided legal paths;
- compose a human-readable response.

Not allowed:
- decide required fields;
- invent schema paths;
- decide workflow order;
- select default vs enrichment vs user value;
- validate contract correctness;
- directly edit draft/session persistence.

### ADCM
Owns:
- raw chat messages and message IDs;
- session state;
- signals and preferences;
- evidence;
- value candidates and deterministic resolution;
- revisions and audit;
- orchestration of MCP calls;
- capability routing;
- projection into contract draft.

### Contract Forge MCP
Owns:
- schema/contract structure;
- legal/allowed paths;
- staged onboarding requirements and order;
- enrichments and defaults with provenance;
- partial/final validation;
- dynamic workflow decisions.

### Schema Explorer and future MCPs
Return findings, evidence, constraints, candidate values or validation results. They do not write the contract draft directly.

## Data pipeline

`Raw user message -> TurnInterpretation -> Signal/Preference/Correction -> candidate creation -> deterministic resolution -> DraftProjector -> ContractDraft`

A pre-path signal example:

`"separator is ;" -> Signal(concept="field_delimiter", value=";")`

Only after Contract Forge exposes `source.delimited.delimiter` as legal can it become a `ValueCandidate` for that path.

## Change guidance

When adding a feature:

1. Identify whether it is semantics, orchestration, contract authority or infrastructure.
2. Put semantic behavior behind `SemanticInterpreterPort`.
3. Put external services behind a port.
4. Keep domain models independent of Pydantic AI, MCP transport, databases and web frameworks.
5. Add tests for any new invariant.
6. Prefer one small application service over introducing a framework/workflow engine.
7. Do not turn ADCM into a second Contract Forge.

## Important files

- `src/adcm/domain/models.py` — domain state and provenance.
- `src/adcm/application/turn_processor.py` — applies one semantic interpretation to state.
- `src/adcm/application/workflow_runner.py` — deterministic MCP fast-forward loop.
- `src/adcm/application/signal_binder.py` — legal Signal -> path binding.
- `src/adcm/application/candidate_resolver.py` — precedence policy.
- `src/adcm/application/draft_projector.py` — schema authority barrier.
- `src/adcm/ports/*` — infrastructure boundaries.
- `src/adcm/adapters/mcp/mock_contract_forge.py` — executable reference behavior.
- `src/adcm/adapters/llm/pydantic_ai_interpreter.py` — optional semantic adapter.

## Anti-patterns

Do not add code resembling:

```python
state.contract_draft.values[llm_path] = llm_value
```

Do not make an agent loop decide which stage Contract Forge should expose next.
Do not use chat history as the only application state.
Do not store enrichment/default provenance only in display text.
Do not immediately map every user statement to a contract path.
