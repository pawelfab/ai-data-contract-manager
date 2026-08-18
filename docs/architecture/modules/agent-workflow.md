---
module: agent-workflow
source_roots:
  - AGENTS.md
  - .github
  - .codex/skills/repository-knowledge
  - scripts/agent
  - githooks
last_verified: working-tree-2026-08-18
owners: []
---

# Repository agent workflow

## Responsibility

Provide fast and reviewed change workflows, repository-specific instructions, safety hooks, deterministic documentation impact/freshness tooling, Git quality hooks, and a reusable repository-knowledge skill.

## Components

- `AGENTS.md` defines source-of-truth order, workflow selection, delegation, contracts, implementation, and documentation completion.
- `.github/agents` and `.github/prompts` expose Copilot agents and slash-command routing.
- `.github/skills/repository-knowledge` is the Copilot skill; `.codex/skills/repository-knowledge` is the Codex-compatible port.
- `.github/hooks/agent-workflow.json` invokes session context, pre-tool safety, and Stop freshness gates.
- `scripts/agent/config.json` (ignored) is the active repository-specific policy; `config.example.json` is its reviewed default.
- `common.py`, `doc_impact.py`, `doc_freshness.py`, `repo_inventory.py`, `quality_gate.py`, and hook scripts implement deterministic support behavior.

## Safety and failure behavior

Git commands use command-scoped `safe.directory=<resolved repository>` and never persist that trust setting. Missing configured source roots raise `RuntimeError`. Configured output paths must remain relative to the repository. Mutating tools targeting protected workflow paths require approval. Recursive Windows deletion and worktree-destructive Git commands match approval patterns.

## Operational commands

See `scripts/agent/README.md`. `validate_setup.py` validates agent references and paths; `doc_impact.py` maps changed sources to curated docs; `repo_inventory.py` regenerates navigation; `doc_freshness.py` compares or records source hashes. Git hook installation is intentionally manual.

## Tests proving behavior

`tests/test_agent_workflow.py` covers installed artifacts, ADCM config mappings, missing-root failure, command-scoped Git worktree detection, path containment, mutation-tool recognition, protected-path normalization, and Windows/Git approval patterns.

