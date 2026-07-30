# Project-wide Copilot instructions

> Replace placeholders in this file with repository-specific facts.

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

The canonical commands are defined in `scripts/agent/config.json`.

Do not invent commands. Read project manifests and CI configuration when the config is incomplete.

## Coding rules

- Match existing naming, typing, error handling, logging, and dependency injection patterns.
- Prefer small changes that reuse existing project abstractions.
- Do not introduce dependencies without explaining why built-in or existing dependencies are insufficient.
- Preserve public compatibility unless the final contract explicitly authorizes a breaking change.
- Validate data at the system boundary and keep domain invariants in the domain layer.
- Never log credentials, tokens, secrets, or sensitive payloads.
- Do not catch broad exceptions without preserving diagnostics and applying project conventions.

## Testing rules

- Add tests for changed behavior, edge cases, error paths, and compatibility.
- Prefer tests at the lowest level that reliably proves the behavior.
- Use integration tests for database, transaction, serialization, framework routing, or external boundary behavior.
- A changed implementation is not complete while relevant configured checks fail.

## Multi-agent workflow

Follow `AGENTS.md`.

Use the Feature Coordinator for complete workflows. Use Repository Guide for read-only questions about current behavior.

Architecture knowledge lives under `docs/architecture/`. Treat its freshness marker as a warning system, not as proof that documentation is correct.
