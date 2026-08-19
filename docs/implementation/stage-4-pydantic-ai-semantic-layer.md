# Stage 4 — Pydantic AI semantic interpretation and response composition

## Goal

ADCM has a production semantic adapter that turns user language into typed `TurnInterpretation` values and a response-composition boundary that turns a stabilized workflow result into user-facing language. The semantic layer may detect intent, extraction, corrections, uncertainty, and typo suggestions, but it never authorizes paths, validates a contract, selects candidate precedence, or mutates `ContractDraft`. Response composition is invoked only after the internal turn has stabilized.

## Why this stage exists

The repository already contains an optional `PydanticAIInterpreter` and a deterministic `RuleBasedInterpreter`. The former is currently a thin adapter, while `ChatService` has no response-composer boundary and workflow tests can be contaminated by parser behavior. This stage makes the LLM boundary explicit and testable before API and UI work exposes user-visible responses.

## Preconditions

- Stages 1–3 are complete, including the owner-approved Forge source/protocol. The mock Forge may still be used as an isolated unit-test double, but it must not bypass an unmet Stage 3 precondition.
- `SemanticInterpreterPort.interpret_turn(text, context)` and typed `TurnInterpretation` models are available.
- Workflow tests can inject a deterministic fake interpretation and do not require a network model.
- The selected Pydantic AI provider/model and credentials are supplied through configuration; tests run without network access.

## Scope

- Complete the `PydanticAIInterpreter` implementation of `SemanticInterpreterPort` using structured `TurnInterpretation` output.
- Keep the system prompt and context contract focused on semantic extraction, correction uncertainty, and typo suggestions; prohibit invented paths, defaults, rules, and required values.
- Define a provider-neutral response-composition port and an adapter that receives only a stable/redacted result and produces natural-language text plus optional clarification prompts.
- Keep deterministic `RuleBasedInterpreter` as an offline/demo adapter and give it independent parser tests (including diacritic folding).
- Add model/provider configuration, timeout/error behavior, redaction/audit boundaries, and tests that prove semantic output cannot directly change workflow state.

## Out of scope / Do not do

- Do not let the LLM parse `contract.json`, `x-contract-rules`, enrichment bundles, or schema revisions.
- Do not expose a tool that writes `ContractDraft`, `ResolvedValue`, `CurrentSchemaView`, or candidates.
- Do not let response composition run before `WorkflowRunner` returns a stable outcome or use chat history as authoritative state.
- Do not add an autonomous agent loop, multi-agent runtime, function-calling graph, or provider-specific code to the domain/application core.
- Do not make workflow tests depend on a live model or the demo NLP vocabulary.

## Architectural boundaries

- **ADCM:** owns structured state, evidence, signals/preferences, candidates, workflow, and the stable response context.
- **Contract Forge:** remains schema/rule/validation/YAML authority; its paths/statuses are supplied to the LLM only as presentation context, never as permission to invent values.
- **LLM/Pydantic AI:** owns semantic interpretation and natural-language composition only.
- **Other MCPs:** are not invoked by the LLM adapter; capabilities remain ADCM-routed.
- **Airflow DAG Generator:** is not described or emulated by prompts; runtime DSL is shown as opaque contract text when needed.

## Invariants

- LLM output never mutates `ContractDraft` directly.
- Schema authority beats semantic inference; the LLM cannot authorize a path or choose precedence.
- Uncertain corrections do not supersede prior state.
- User-origin signals/preferences created from an interpretation receive Evidence in `TurnProcessor` before binding.
- Conversation history is semantic context/evidence, not authoritative application state.
- User-visible text is generated only after workflow stabilization.
- Hidden model reasoning/chain-of-thought is never persisted or claimed in audit.

## Files affected

| File | Action | Purpose |
|---|---|---|
| `src/adcm/adapters/llm/pydantic_ai_interpreter.py` | MODIFY | Implement structured semantic interpretation, provider errors, timeouts, and context redaction. |
| `src/adcm/adapters/llm/rule_based_interpreter.py` | MODIFY if needed | Keep deterministic offline behavior and language normalization isolated. |
| `src/adcm/ports/semantic_interpreter.py` | MODIFY | Clarify typed interpreter contract and semantic-only guarantees. |
| `src/adcm/ports/response_composer.py` | NEW | Define provider-neutral post-stabilization response composition boundary. |
| `src/adcm/application/response_composer.py` | NEW | Adapt stable workflow/context data to the response port without changing domain state. |
| `src/adcm/domain/models.py` | MODIFY if required | Add typed, redacted response context/result models; do not add provider types. |
| `src/adcm/config.py` | MODIFY | Configure model/provider/timeouts and response mode without embedding secrets. |
| `tests/test_rule_based_interpreter.py` | MODIFY | Parser-only extraction, typo, diacritic, and uncertainty cases. |
| `tests/test_pydantic_ai_interpreter.py` | NEW | Mock structured model output, malformed output, timeout, and prompt-boundary behavior. |
| `tests/test_response_composer.py` | NEW | Stable-outcome-only invocation and redaction/formatting contract. |
| `tests/test_workflow.py` | MODIFY | Ensure workflow tests use typed fakes and remain parser-independent. |
| `docs/ARCHITECTURE.md` | MODIFY | Keep the LLM/ADCM/Forge responsibility split current. |
| `docs/TESTING_STRATEGY.md` | MODIFY | Record separation of semantic and workflow tests. |
| `docs/ADAPTERS_AND_DEPLOYMENT.md` | MODIFY | Describe model/provider selection and offline fallback. |

## Public contracts

Existing semantic contract:

```python
async def interpret_turn(text: str, context: AgentContext) -> TurnInterpretation: ...
```

New response boundary (names are public and may be implemented by any provider):

```python
class ResponseComposerPort(Protocol):
    async def compose(self, context: ResponseContext) -> ComposedResponse: ...
```

`ResponseContext` must contain a stable `WorkflowOutcome`, safe draft/read-model data, pending requirements or external-block reason, and bounded recent messages. `ComposedResponse` contains user-visible text and optional structured clarification items; it does not contain hidden reasoning, provider traces, or mutable domain objects. The concrete provider may be deterministic for tests.

`TurnInterpretation` keeps `intent`, `extracted_signals`, `preferences`, `corrections`, and `possible_typos`. A correction with `intent="uncertain"` is advisory and must not change state.

## Inputs and outputs

The interpreter receives user text plus `AgentContext` (current stage, active semantic views, known resolved values, currently allowed paths for explanation only, pending requirements, bounded recent messages). It returns a Pydantic-validated `TurnInterpretation` with schema-agnostic concepts. The response composer receives a stable, redacted context and returns text/clarifications. Neither boundary returns a draft mutation command.

## State ownership

ADCM persists the raw user message as Evidence and applies the interpretation through `TurnProcessor`. The LLM adapter owns no session, candidate, revision, or draft state. Response composition is read-only. Provider conversation memory, if any, is disabled or bounded and never becomes authoritative state.

## Data flow

```text
user text + AgentContext
        -> SemanticInterpreterPort (Pydantic AI or deterministic fake)
        -> TurnProcessor creates Evidence/signals/preferences/revisions
        -> WorkflowRunner stabilizes ADCM/Forge state
        -> stable ResponseContext
        -> ResponseComposerPort
        -> user-visible text/clarification
```

## Required behavior / how it should work

1. Instruct the semantic model to extract concepts, not contract paths, and to represent broad statements as preferences.
2. Emit explicit corrections only when replacement intent is clear; emit `uncertain` otherwise. Typos are suggestions, not silent rewrites.
3. Validate model output as `TurnInterpretation`; malformed/unknown fields are a semantic adapter error, not a reason to mutate state heuristically.
4. Keep model/context payloads bounded and redact secrets/credentials; never include hidden provider messages in audit.
5. For response composition, pass the final stable status (`WAITING_FOR_USER`, `BLOCKED_EXTERNAL`, `COMPLETE`, `INVALID`, or `FAILED`) and the appropriate safe explanation. The composer must not re-run Forge or capabilities.
6. If the model/provider fails, surface a typed application failure and leave the pre-turn domain state recoverable; do not fabricate a successful interpretation.
7. Keep `RuleBasedInterpreter` behavior deterministic and test its parser separately from `WorkflowRunner`.

## Forbidden implementation shortcuts

- Passing raw model output dictionaries into `TurnProcessor` without Pydantic validation.
- Allowing the model to emit or execute arbitrary contract paths, defaults, rule IDs, or precedence decisions.
- Using a model-generated response as evidence of a business value.
- Calling the composer inside the fast-forward loop or before final validation/dependency resolution.
- Persisting chain-of-thought, hidden prompts, or provider internal traces as audit events.
- Making tests pass by weakening the semantic system prompt while workflow tests still depend on parser quirks.

## Error semantics

- Missing optional Pydantic AI dependency: adapter construction raises a clear configuration error; offline tests use `RuleBasedInterpreter`/fake.
- Provider timeout/unavailable/auth failure: typed semantic error; no state mutation from that turn.
- Invalid structured output: semantic contract error with safe diagnostic; no heuristic fallback unless explicitly configured to use the deterministic adapter.
- Composer failure after a stable turn: preserve persisted state and expose a response-generation failure; it must not roll back valid domain state.

## Status semantics

The LLM and composer do not define workflow statuses. They consume and explain the canonical ADCM statuses only. They must not introduce `DEFERRED` as a top-level outcome or reinterpret `BLOCKED_EXTERNAL` as a user requirement.

## Schema revision semantics

The interpreter may display the current schema stage/revision for context, but it cannot accept, change, or compare revisions. Revision consistency is enforced by WorkflowRunner and Forge.

## Rendering semantics

The composer may mention a rendered YAML artifact only if the stable response context says it exists. It never invokes `render_yaml`; rendering/cache remain application capabilities after stabilization.

## Template semantics

Prompts must treat `{source}` and runtime `{{...}}` strings as literal contract values. The LLM must not translate runtime DSL into Airflow/Jinja or consume it as a date/env value.

## Arrays and paths

The interpreter emits concepts and values, not concrete array paths. If a user describes a column or table index, preserve that as semantic data for later binding; only Forge-authorized paths and ADCM projection can create an instance path.

## Value precedence

The interpreter never ranks candidates. It may express confidence and correction intent; `CandidateResolver` and Forge metadata determine the winner deterministically.

## Tests

- **Semantic unit:** extraction, preference detection, explicit/uncertain corrections, typo suggestions, diacritic folding, structured-output validation, and provider failure.
- **Workflow isolation:** `WorkflowRunner` tests inject typed fake interpretations; no live model or parser vocabulary is required.
- **Boundary negative:** attempted path/default/precedence injection is rejected or ignored as semantic output and cannot mutate `ContractDraft`.
- **Response contract:** composer is called only with a stable outcome, returns safe text, and does not call Forge/capabilities.
- **Audit/privacy:** no hidden reasoning or secret prompt material is persisted.

## Acceptance criteria

- `PydanticAIInterpreter` returns only validated `TurnInterpretation` values and has no direct dependency on application/domain mutation APIs.
- Deterministic parser tests pass independently of workflow tests.
- Uncertain corrections leave prior signals/candidates active; explicit corrections flow through normal Evidence/revision handling.
- Response composition is impossible before a stable workflow result by type/ordering tests.
- Provider errors leave state recoverable and visible.

## Explicit non-goals

HTTP idempotency, durable session concurrency, read-only UI, production Forge integration details, and release gates are later stages. No autonomous model tool loop is introduced.

## Documentation updates

Update `docs/ARCHITECTURE.md`, `docs/TESTING_STRATEGY.md`, `docs/ADAPTERS_AND_DEPLOYMENT.md`, `LLM_REPO_GUIDE.md`, and relevant port/symbol docs. Record the response-composer boundary and audit redaction decision in `docs/DESIGN_DECISIONS.md`.

## Completion checklist

- [ ] Semantic interpreter and response composer ports are typed and provider-neutral.
- [ ] LLM instructions forbid path authorization, validation, precedence, and hidden-state mutation.
- [ ] Parser and workflow tests are independent.
- [ ] Stable-outcome-only response ordering is verified.
- [ ] Provider failures and privacy boundaries are covered.
