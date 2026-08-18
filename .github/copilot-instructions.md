# Project-wide Copilot instructions

These facts are verified against `pyproject.toml`, `src/adcm`, tests, and `LLM_REPO_GUIDE.md`.

## Project identity

- Product/domain: AI Data Contract Manager (ADCM), a schema-authoritative conversational orchestrator for data-contract onboarding through MCP capabilities.
- Primary language: Python.
- Frameworks/libraries: Pydantic v2, Pydantic AI, MCP, jsonschema, pytest.
- Runtime: Python `>=3.11`.
- Package/build tools: Hatchling and pip; pytest for tests.
- Deployment target: reference Python package/prototype. No deployment manifest is present.

## Architecture

- Architectural style: small layered/ports-and-adapters Python package.
- Dependency direction: adapters implement ports; application orchestrates domain types and ports; domain models remain independent of transports, persistence, and Pydantic AI.
- Main source root: `src/adcm`.
- Test root: `tests`.
- Contract/schema inputs: `contracts` and `examples/contract-rules.json`.
- Migration roots: none in the current repository.
- Generated documentation root: `docs/architecture/generated`; regenerate its contents instead of editing them by hand.

## Domain invariants

- Contract Forge is authoritative for legal paths, workflow order, requirements, defaults, enrichments, and validation.
- The LLM and external MCP results never mutate `ContractDraft` directly.
- `Signal` remains schema-agnostic until `SignalBinder` sees one unambiguous authorized path.
- `CandidateResolver` selects candidates deterministically; `DraftProjector` projects only currently authorized paths.
- Corrections supersede historical facts and append revision evidence instead of deleting history.

## Commands

Canonical commands are defined in `scripts/agent/config.json` after setup. The repository-specific test gate is `python -m pytest -q`. Ruff is not a gate because it is not installed by the declared development dependencies.

Do not invent commands. Inspect manifests and CI when configuration is incomplete.

## Coding rules

- Match existing naming, typing, errors, logging, dependency injection, and module boundaries.
- Prefer the smallest coherent change using existing abstractions.
- Do not add dependencies without explaining why current dependencies are insufficient.
- Preserve public compatibility unless explicitly authorized.
- Validate input at boundaries and preserve domain invariants in the proper layer.
- Never log credentials, tokens, secrets, or sensitive payloads.
- Do not catch broad exceptions without preserving diagnostics and following repository conventions.

## Testing rules

- Add tests for changed behavior, edge cases, error paths, and compatibility.
- Prefer the lowest test level that reliably proves behavior.
- Use integration tests for database, transaction, serialization, routing, and external-boundary behavior.
- Work is not complete while relevant configured checks fail.

## Workflow commands

Follow `AGENTS.md`.

- `/plan-change-preview`: quick plan in chat, no files changed.
- `/plan-change`: quick one-agent plan saved as a contract.
- `/plan-change-reviewed`: independently reviewed multi-agent contract.
- `/implement-change`: quick one-agent implementation with tests and automatic documentation synchronization.
- `/implement-change-reviewed`: contract-first implementation with independent review and documentation synchronization.
- `/review-current-change`: independent review of the current diff without editing.
- `/explain-current`: read-only explanation of current behavior.
- `/sync-architecture-docs`: synchronize documentation to current code.

Architecture knowledge lives under `docs/architecture/`. A current freshness marker proves only that configured source hashes have not changed since the last explicit synchronization; code and tests remain the source of truth.
