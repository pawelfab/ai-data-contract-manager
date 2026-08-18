---
flow: repository-agent-change
entry_points:
  - AGENTS.md
  - .github/prompts/implement-change.prompt.md
  - .github/prompts/implement-change-reviewed.prompt.md
last_verified: working-tree-2026-08-18
---

# Repository change workflow

## Routing

- Fast planning/implementation uses `Planner Fast` or `Feature Fast` without subagents.
- Reviewed planning/implementation uses `Feature Coordinator`, bounded verifiers, contract review/finalization, implementation review, and Docs Updater.
- Explain, review-only, documentation sync, and bootstrap modes do not authorize unrelated application edits.

## Change completion

1. Read `AGENTS.md`, repository instructions, freshness, relevant curated docs, and generated map.
2. Inspect only affected code/tests and preserve unrelated worktree changes.
3. For reviewed implementation, require a current `STATUS: FINAL` contract; fast implementation may use a matching contract or a session TODO.
4. Implement and test the smallest coherent change.
5. Run `doc_impact.py --working-tree --write` and update only impacted curated docs, or record a specific no-impact exception.
6. Regenerate inventory, mark verified docs current, and check freshness.
7. Run configured quality stages and report all failures.

## Safety hooks

SessionStart records a source-hash baseline. PreToolUse evaluates deny/approval patterns and protected paths. Stop blocks only when this session changed configured source and strict freshness/quality conditions fail. Git pre-commit checks staged documentation evidence; pre-push checks freshness and configured quality stages.

## State and side effects

Local config is ignored at `scripts/agent/config.json`; session baselines are ignored under `.agent-state`. Generated inventory and freshness files are repository artifacts. Installing Git hooks is a separate explicit action because it changes `core.hooksPath`.

