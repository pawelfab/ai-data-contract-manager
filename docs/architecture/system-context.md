---
last_verified: working-tree-2026-08-18
---

# ADCM system context

## Purpose

AI Data Contract Manager is a Python reference implementation of a schema-authoritative conversational orchestrator. It converts user language into evidence, schema-agnostic signals/preferences, deterministic candidates, resolved values, and a nested contract draft while Contract Forge remains authoritative for the schema and validation.

Evidence: `readme.md`, `LLM_REPO_GUIDE.md`, `src/adcm/domain/models.py::ConversationState`, `src/adcm/application/chat_service.py::ChatService`.

## Users and external systems

- A caller/UI sends user text and a session UUID to `ChatService.handle_user_message`.
- A `SemanticInterpreterPort` implementation extracts typed meaning; `PydanticAIInterpreter` is the optional model-backed adapter.
- Stateless Contract Forge implements `ContractForgePort.evaluate_draft`, `validate_final`, and `render_yaml`.
- Contract Forge consumes `contracts/contract.json` together with `contracts/ux_rules.json`; the reference package does not evaluate those artifacts inside ADCM.
- Future MCPs implement capability handlers and are selected by `CapabilityRouter`.

## Major runtime components

- Domain state and provenance: `src/adcm/domain/models.py` and `contract_path.py`.
- Deterministic application orchestration: `src/adcm/application/`.
- External boundaries: `src/adcm/ports/`.
- Reference adapters: `src/adcm/adapters/`.
- Repository workflow: `.github/`, `.codex/skills/repository-knowledge/`, and `scripts/agent/`.

## Data stores and side effects

- `InMemorySessionRepository` deep-copies state for ephemeral use.
- `JsonFileSessionRepository` persists one JSON file per session UUID.
- `JsonlAuditSink` appends serialized audit events to a JSONL file.
- The repository workflow writes generated navigation under `docs/architecture/generated`, freshness state to `.freshness.json`, and ignored session baselines under `.agent-state/`.

## Trust boundaries and constraints

- Neither an LLM nor an external capability may mutate `ContractDraft` directly.
- `DraftProjector.project` rebuilds a nested draft only from resolved values allowed by the latest `CurrentSchemaView`.
- `CurrentSchemaView` is replaced after every Forge evaluation; historical allowed paths are not accumulated.
- FINAL rendering requires a VALID receipt for the same draft hash and schema revision.
- Domain code must not depend on Pydantic AI, MCP transport, persistence, or deployment frameworks.

## Runtime and commands

- Python `>=3.11`; Hatchling build metadata is in `pyproject.toml`.
- Tests: `python -m pytest -q`.
- Workflow validation: `python scripts/agent/validate_setup.py`.
- Inventory: `python scripts/agent/repo_inventory.py`.
- Documentation impact: `python scripts/agent/doc_impact.py --working-tree --write`.
- Freshness: `python scripts/agent/doc_freshness.py --check --json`.

## Known gaps

- The repository is a reference package, not a deployed UI/service; no deployment manifest or database migration tree exists.
- `contracts/contract.json` exposes the canonical `metadata.sourceSystemGcpId`, `converter`, and `preparator` paths used by the ROCKET/SAP UX rules; legacy rule annotations remain covered by the contract artifact test.
- Ruff configuration exists in `pyproject.toml`, but Ruff is not installed by current project dependencies and is not a workflow gate.
