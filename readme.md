# ADCM reference architecture

ADCM is a small, schema-authoritative conversational orchestrator for building data-contract drafts around MCP tools.

The architecture intentionally separates language understanding from contract authority:

- **LLM / Pydantic AI** understands user intent, extracts schema-agnostic signals, detects corrections and likely typos.
- **ADCM** owns chat/session state, evidence, revisions, value candidates, resolution, audit and draft projection.
- **Contract Forge MCP** owns contract schema, allowed paths, workflow/order, requirements, enrichments, defaults and validation.
- **Other MCPs** such as Schema Explorer provide evidence/findings/candidates but never mutate the draft directly.

Core invariant: **a value can enter `ContractDraft` only when its path has been authorized by Contract Forge.**

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\\Scripts\\activate
pip install -e '.[dev]'
pytest
```

Optional Pydantic AI adapter:

```bash
pip install -e '.[ai,dev]'
```

Run the deterministic demo:

```bash
python examples/demo_flow.py
```

Read these first:

- `docs/ARCHITECTURE.md` — complete architecture and boundaries.
- `docs/DOMAIN_MODEL.md` — Signal → Candidate → ResolvedValue → Draft.
- `docs/TURN_LIFECYCLE.md` — exact processing sequence of each user turn.
- `docs/MCP_CONTRACT.md` — expected Contract Forge / future MCP integration contract.
- `docs/ADAPTERS_AND_DEPLOYMENT.md` — local/cloud/provider substitution.
- `LLM_REPO_GUIDE.md` — operational guide for an LLM coding agent reading this repository.

## What this repository is

This is a **reference implementation and architecture skeleton**, not a full production UI or a full Contract Forge MCP server. It contains working domain/application logic, persistence/audit ports, a mock Contract Forge adapter, tests and an optional Pydantic AI semantic-interpreter adapter.

The intent is to keep ADCM small: orchestration and state are deterministic Python; LLM is used only where semantics are required.
