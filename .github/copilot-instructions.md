# Project-wide Copilot instructions

## Project identity

- Product/domain: conversational data-contract creation
- Primary languages: Python, JSON, Markdown
- Frameworks: FastAPI, Pydantic AI, MCP, JSON Schema
- Runtime versions: Python 3.11+
- Package/build tools: pip, setuptools, pytest
- Deployment target: independent services locally and on Cloud Run

## Architecture

- Architectural style: service-oriented monorepo
- Dependency direction: ADCM calls Contract Forge only through MCP; services never import each other's Python package
- Main source roots: `ai-data-contract-manager/src`, `mcp-servers/mcp-contract-forge/src`
- Test roots: `ai-data-contract-manager/tests`, `mcp-servers/mcp-contract-forge/tests`
- Contract/config roots: `mcp-servers/mcp-contract-forge/config`, `mcp-servers/mcp-contract-forge/contracts`
- Generated documentation root: `docs/generated`

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

Architecture knowledge lives under the root `docs/`. Treat its freshness marker as a warning system, not as proof that documentation is correct.
