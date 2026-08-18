# Implementation roadmap

## Phase 1 — current package

- Domain state and provenance models.
- Schema-agnostic signals and cross-cutting preferences.
- Deterministic resolver and draft projector.
- Staged mock Contract Forge.
- Session ports/adapters.
- Optional Pydantic AI semantic adapter.
- Unit/integration tests.

## Phase 2 — real Contract Forge MCP adapter

- Implement Streamable HTTP/required transport.
- Normalize real MCP tool outputs to `RequirementBundle`.
- Add partial/final validation mapping.
- Persist tool-call IDs in evidence.

## Phase 3 — response composition

- Add typed `ResponseContext` and separate response composer.
- Present origins such as user/default/enrichment succinctly.
- Ask only unresolved requirements returned after workflow fast-forward.
- Surface typo confirmation when confidence policy requires it.

## Phase 4 — Schema Explorer

- Add `SchemaExplorerPort`/capability adapter.
- Route Contract Forge capability requests.
- Store table-existence/schema findings as evidence.
- Add candidates/validation findings without direct draft mutation.

## Phase 5 — durable production persistence

- Durable session store.
- Separate audit sink.
- Revision snapshots/event retention policy.
- Correlation IDs across chat/LLM/MCP calls.

## Phase 6 — GitHub enrichment inside Contract Forge

- Add `GitHubEnrichmentRepository` behind Contract Forge's own repository port.
- Keep ADCM API unchanged.
