---
scope: scripts/agent
last_verified: working-tree-2026-08-18
---

# Symbol catalog: repository agent workflow

| Path | Symbol | Contract |
|---|---|---|
| `common.py` | `load_config` | Load ignored local config when present, otherwise reviewed example. |
| `common.py` | `run_git` | Run Git with command-scoped safe-directory for the resolved repository root. |
| `common.py` | `source_files` | Enumerate configured tracked/untracked source files; raise when no root exists. |
| `common.py` | `current_source_hashes`, `current_architecture_doc_hashes`, `hash_delta` | Deterministic freshness inputs/deltas. |
| `doc_impact.py` | `infer_docs`, `render_markdown` | Map changed relevant paths to configured curated docs. |
| `doc_freshness.py` | `compare`, `mark_current`, `check_staged` | Compare schema-v2 marker, enforce curated evidence, and write explicit current/no-impact state. |
| `repo_inventory.py` | `inspect`, `render_map`, `main` | Extract Python/generic symbols and write JSON/Markdown navigation. |
| `security_guard.py` | `is_mutating_tool`, `contains_protected_path`, `main` | Deny/ask/allow PreToolUse decisions. |
| `session_context.py` | `cleanup_state`, `main` | Record per-session source baseline and additional context. |
| `stop_gate.py` | `load_session_state`, `main` | Block only session source changes with stale docs or configured Stop failures. |
| `quality_gate.py` | `run_stages`, `main` | Run trusted configured commands and preserve failures. |
| `validate_setup.py` | `is_repo_relative_path`, `main` | Validate required files, prompt-agent references, tool separation, config keys, and contained paths. |
| `setup_workflow.py` | `run`, `main` | Create local config, validate, generate inventory, and optionally install hooks/mark initial docs. |
| `install_git_hooks.py` | `main` | Explicitly set `core.hooksPath=githooks`. |

## Configuration keys

`source_roots`, `documentation_relevant_patterns`, evidence/non-evidence patterns, `documentation_map`, quality stages, strict/marker gates, protected paths, and deny/approval regexes are defined in `scripts/agent/config.example.json`; `config.json` is the ignored active copy.

