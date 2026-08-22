# AI Data Contract Manager system

Monorepo of independently versioned and deployed services.

- `ai-data-contract-manager/` — conversational ADCM service and the only service that owns the user conversation and PydanticAI orchestration/heuristics.
- `mcp-servers/mcp-contract-forge/` — deterministic Contract Forge MCP service.
- `docs/` — system-level architecture and protocol documentation.

Each service has its own `pyproject.toml`, `.venv`, dependencies, tests, Dockerfile, documentation and version. Services never import runtime Python code from each other.

Core architecture rule: Contract Forge is a mandatory deterministic dependency of ADCM. Atlassian, repository, schema-explorer and visualizer MCPs are optional/agentic tools available through ADCM's PydanticAI layer. Forge is never placed in the agent's free tool-choice set.

Forge isolates both contract-format evolution and enrichment evolution behind separate ports. Current enrichment is JSON-backed; a per-user repository can later be added without changing ADCM or Forge evaluation logic.

## Mandatory architecture contract

Before any architecture planning, feature implementation or LLM-assisted refactor, read [`docs/architecture-guardrails.md`](docs/architecture-guardrails.md). It defines which service owns each responsibility, how contract/enrichment evolution must remain localized, how PydanticAI and MCPs are split, and the anti-patterns that require redesign.

Coding agents should also read [`AGENTS.md`](AGENTS.md). A structural change to `contract.json` must normally be contained in the Contract Forge contract-format adapter; a change of enrichment persistence must normally be contained behind `EnrichmentRepositoryPort`. Neither should propagate through ADCM.


## Consolidated v0.4 behavior

The current package includes progressive source-system-first discovery, fillable requirements, data-driven global/system enrichment, deterministic ADCM candidate validation, edit-after-complete behavior and fixed-point convergence guards. See `docs/CURRENT_STATE.md`, `docs/DECISIONS.md` and `docs/KNOWN_ISSUES.md` before extending it.

The supplied latest contract artifact is preserved unchanged by Forge as `resources/contract.input.json`. The runtime `resources/contract.json` contains a documented minimal repair for dangling local `$ref` definitions in that artifact; see `mcp-servers/mcp-contract-forge/docs/contract-repair-note.md`. Replace those inferred definitions with authoritative schema definitions when available.
