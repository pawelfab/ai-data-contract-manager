# ADCM implementation plan

## Overall goal

Evolve the current corrected reference package into a production-capable, schema-authoritative conversational orchestrator without moving Contract Forge authority, path authorization, validation, or YAML rendering into ADCM.

The detailed implementation contracts live under `docs/implementation/`. Implement one stage at a time and stop when a stage precondition is false.

## Stage order and status

| Stage | Capability | Status | Specification |
|---|---|---|---|
| 0 | Repository baseline, configuration, and Contract Forge artifact ownership | READY | [Stage 0](docs/implementation/stage-0-repository-and-contract-ownership.md) |
| 1 | Domain model, provenance, deterministic resolution, paths, and projection | NOT_STARTED | [Stage 1](docs/implementation/stage-1-domain-model-and-deterministic-projection.md) |
| 2 | Fast-forward workflow, schema-view replacement, corrections, and capabilities | NOT_STARTED | [Stage 2](docs/implementation/stage-2-workflow-fast-forward-and-capabilities.md) |
| 3 | Real stateless Contract Forge transport and provider conformance | BLOCKED_INPUT | [Stage 3](docs/implementation/stage-3-stateless-contract-forge-integration.md) |
| 4 | Pydantic AI semantic interpretation and response composition | NOT_STARTED | [Stage 4](docs/implementation/stage-4-pydantic-ai-semantic-layer.md) |
| 5 | Durable versioned sessions and idempotent audit delivery | NOT_STARTED | [Stage 5](docs/implementation/stage-5-durable-session-and-audit.md) |
| 6 | Turn completion, HTTP API, idempotency, and post-stabilization response | NOT_STARTED | [Stage 6](docs/implementation/stage-6-api-chat-and-turn-completion.md) |
| 7 | Read-only Web UI, draft/YAML read models, and artifact reuse | NOT_STARTED | [Stage 7](docs/implementation/stage-7-web-ui-and-read-models.md) |
| 8 | Real-contract end-to-end hardening and release gates | NOT_STARTED | [Stage 8](docs/implementation/stage-8-end-to-end-hardening.md) |

`BLOCKED_INPUT` on Stage 3 means the repository now contains the requested local `contracts/ux_rules.json` fixture, but still lacks an agreed source location/endpoint and transport contract for the production Contract Forge implementation. No production ownership is inferred from the local fixture.

## Dependency graph

```text
Stage 0 -> Stage 1 -> Stage 2 -> Stage 3 -> Stage 4
                                               |
                                               v
Stage 8 <- Stage 7 <- Stage 6 <- Stage 5 <-----+
```

The order is intentionally linear for implementation. Evidence gathered for a later stage may be prepared earlier, but no later-stage contract may be used to bypass an unmet precondition.

## Global decisions and invariants

- ADCM owns conversation, evidence, signals, preferences, candidates, revisions, draft state, orchestration, capability routing, and presentation state.
- Contract Forge is stateless and owns canonical schema paths, progressive requirements, defaults, enrichments, rule evaluation, validation, and canonical YAML.
- LLM output and external MCP output never mutate `ContractDraft` directly.
- `CurrentSchemaView` replaces the prior view; draft projection never accumulates historical allowed paths.
- User-origin signals/preferences/candidates require Evidence, and history is superseded rather than deleted.
- Candidate resolution is deterministic, preserves ADCM origin precedence, and never uses UUID ordering.
- `ContractDraft` is nested JSON/YAML-shaped data and supports concrete array instance paths.
- Forge schema revision is an explicit consistency token; it is not part of `draft_hash`.
- Rendering is separate from evaluation and occurs after turn stabilization; FINAL requires matching VALID final validation.
- Forge preserves runtime Contract DSL (`{{...}}`); the Airflow DAG Generator translates it later.
- No production schema or enrichment evaluator may be added under `src/adcm`.
