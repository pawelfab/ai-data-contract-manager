# Project-wide Copilot instructions

> Replace placeholders with repository-specific facts before relying on autonomous changes.

## Project identity

- Product/domain: `<describe the product>`
- Primary languages: `<languages>`
- Frameworks: `<frameworks>`
- Runtime versions: `<versions>`
- Package/build tools: `<tools>`
- Deployment target: `<target>`

## Architecture

- Architectural style: `<modular monolith / services / layered / hexagonal / other>`
- Dependency direction: `<rules>`
- Main source roots: `<paths>`
- Test roots: `<paths>`
- Migration roots: `<paths>`
- Generated code roots: `<paths; never edit manually>`

## Commands

Canonical commands are defined in `scripts/agent/config.json` after setup.

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
