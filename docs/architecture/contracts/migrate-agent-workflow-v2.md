STATUS: FINAL

# Migrate repository agent workflow to v2

## 1. Scope and non-goals

Migrate the existing v1 repository-agent workflow from `new-agent/` into its operational locations, adapt generic configuration to ADCM, expose the repository-knowledge skill to both GitHub Copilot and Codex, and bootstrap the missing `docs/architecture/` knowledge base.

Non-goals:

- Do not modify `src/adcm/` application behavior.
- Do not resolve or overwrite the pre-existing working-tree changes under `contracts/`, `examples/`, or `tests/test_contract_schema_rules.py`.
- Do not install dependencies, configure global Git trust, install Git hooks, or delete `new-agent/`.
- Do not install package-only files `new-agent/CHANGELOG.md`, `new-agent/MIGRATION_FROM_V1.md`, `new-agent/VERSION`, `new-agent/sample.txt`, or the ambiguous empty `new-agent/gitkeep`.

## 2. Confirmed current behavior

- `AGENTS.md` defines the v1 contract-first workflow and requires a final reviewed contract before implementation.
- `.github/agents/`, `.github/prompts/`, `.github/hooks/`, `.github/skills/repository-knowledge/`, `scripts/agent/`, `githooks/`, and `.vscode/` already contain v1 workflow files.
- `new-agent/MIGRATION_FROM_V1.md` identifies the package as v2.0.0 and names both replacements and new files.
- `docs/architecture/README.md`, `.freshness.json`, and `generated/repository-map.md` are absent, although the current agents refer to them.
- `.github/copilot-instructions.md` still contains repository placeholders.
- `scripts/agent/config.json` is absent; `config.example.json` is generic and has no quality commands.
- `pyproject.toml` confirms Python `>=3.11`, Hatchling, pytest configuration, and a Ruff section, but Ruff is not installed in either tested interpreter.
- Read-only Git commands require a command-scoped `safe.directory` override in this execution environment because repository ownership differs from the sandbox account.
- The working tree already contains unrelated user changes: deleted `contracts/data-contract.schema.json` and untracked `contracts/contract.json`, `examples/contract-rules.json`, and `tests/test_contract_schema_rules.py`.

## 3. Proposed flow

1. Copy v2 agents, prompts, hook configuration, support scripts, templates, editor tasks, and Git hook scripts to their established v1 locations.
2. Merge repository-specific ADCM facts into `AGENTS.md` and `.github/copilot-instructions.md` instead of retaining placeholders.
3. Adapt `scripts/agent/config.example.json`, create ignored `scripts/agent/config.json`, harden repository-path and protected-file checks, and update `.gitignore` plus support-script documentation.
4. Port `repository-knowledge` to `.codex/skills/repository-knowledge/`, using Codex-compatible frontmatter and generated `agents/openai.yaml`; keep the Copilot copy under `.github/skills/`.
5. Create curated architecture documents from confirmed code, tests, existing `docs/*.md`, and `LLM_REPO_GUIDE.md`; generate the mechanical inventory and freshness marker only after verification.
6. Validate frontmatter, references, scripts, config, skill structure, architecture freshness, and the repository test suite.

## 4. Exact file and symbol changes

### Replaced from the package

- `AGENTS.md` — v2 routing, fast/reviewed modes, delegation, documentation gate.
- `.github/agents/*.agent.md` — replace the nine existing worker/coordinator definitions; add `Feature Fast` and `Planner Fast`.
- `.github/prompts/*.prompt.md` — replace five existing prompts; add the four v2 fast/reviewed/review prompts.
- `.github/hooks/agent-workflow.json` — v2 SessionStart, PreToolUse, and Stop commands.
- `.github/skills/repository-knowledge/SKILL.md` and `templates/{change-contract,flow,module,review-report,symbol-catalog}.md`.
- `scripts/agent/{common,doc_freshness,quality_gate,repo_inventory,security_guard,session_context,stop_gate,install_git_hooks}.py`.
- `githooks/{pre-commit,pre-push}`.
- `.vscode/{settings,tasks}.json` and `.gitignore.template`.

### New package files

- `.github/agents/{feature-fast,planner-fast}.agent.md`.
- `.github/prompts/{plan-change-preview,plan-change-reviewed,implement-change-reviewed,review-current-change}.prompt.md`.
- `scripts/agent/{doc_impact,setup_workflow,validate_setup}.py`.

### Repository-specific adaptations

- `.github/copilot-instructions.md` — ADCM identity, dependency direction, invariants, paths, and canonical commands.
- `.gitignore` — ignore `scripts/agent/config.json` and `.agent-state/` while preserving current entries.
- `scripts/agent/config.example.json` and ignored `scripts/agent/config.json` — use the exact configuration values specified in section 5.
- `scripts/agent/common.py::run_git` — prepend command-scoped `-c safe.directory=<resolved ROOT>` to every Git invocation; do not write local or global Git configuration.
- `scripts/agent/common.py::source_files` — raise `RuntimeError("None of the configured source_roots exists")` when no configured source root exists instead of scanning every matching repository file. `current_source_hashes`, inventory, freshness, session, impact, and hook callers propagate the error and fail non-zero.
- `scripts/agent/security_guard.py` — recognize shell/command/patch mutation tools case-insensitively, protect prompts/editor/Codex-skill paths, and require approval for common PowerShell/CMD and Git worktree-destructive commands.
- `scripts/agent/setup_workflow.py::run` — invoke subprocess scripts with `sys.executable` so setup stays in the selected interpreter/venv.
- `scripts/agent/validate_setup.py` — reject configured output/state paths that resolve outside the repository root.
- `scripts/agent/README.md` — document v2 setup, validation, impact, inventory, freshness, quality, and hook commands.
- `.codex/skills/repository-knowledge/SKILL.md`, `agents/openai.yaml`, and `templates/{change-contract,flow,module,review-report,symbol-catalog}.md` — NEW Codex port of the repository skill.
- `docs/architecture/README.md` and `docs/architecture/system-context.md` — NEW index and verified system context.
- `docs/architecture/modules/{application,domain,ports,adapters,contract-schema,agent-workflow}.md` — NEW curated module descriptions.
- `docs/architecture/flows/{turn-lifecycle,contract-forge-workflow,agent-change-workflow}.md` — NEW curated execution flows.
- `docs/architecture/symbols/{application,domain,ports,adapters,agent-workflow}.md` — NEW curated symbol catalogs.
- `docs/architecture/generated/{repository-inventory.json,repository-map.md,documentation-impact.md}` and `.freshness.json` — NEW generated state.
- `tests/test_agent_workflow.py` — NEW deterministic checks for repository-specific config, documentation mappings, path containment, protected-file guard decisions, and required installed files.

## 5. Method, function, and configuration contracts

Package script function signatures remain as supplied by v2 except for small NEW internal hardening helpers, including:

- `scripts/agent/common.py::load_config() -> dict[str, Any]`
- `scripts/agent/common.py::run_git(args: list[str], check: bool = False) -> subprocess.CompletedProcess[str]` — execute `git -c safe.directory=<ROOT> ...` with `cwd=ROOT`; never persist trust configuration.
- `scripts/agent/common.py::source_files(config: dict[str, Any]) -> list[Path]`
- `scripts/agent/doc_impact.py::infer_docs(paths: list[str], config: dict[str, Any]) -> dict[str, Any]`
- `scripts/agent/doc_freshness.py::compare(config: dict[str, Any]) -> dict[str, Any]`
- `scripts/agent/doc_freshness.py::mark_current(config: dict[str, Any], reason: str, allow_no_doc_change: bool) -> tuple[bool, dict[str, Any]]`
- `scripts/agent/quality_gate.py::run_stages(stages: list[str], config: dict[str, Any]) -> tuple[bool, list[dict[str, Any]]]`
- `scripts/agent/validate_setup.py::main() -> int`
- `scripts/agent/validate_setup.py::is_repo_relative_path(value: str) -> bool` — NEW; accept only paths resolving inside `ROOT`.
- `scripts/agent/security_guard.py::is_mutating_tool(tool_name: str) -> bool` — NEW; case-fold and return true when the name contains one of `edit`, `create`, `delete`, `write`, `terminal`, `execute`, `shell`, `command`, `apply_patch`, `patch`, `replace`, or `insert`; return false for read/search/list/view names.
- `scripts/agent/security_guard.py::contains_protected_path(text: str, paths: list[str]) -> bool` — NEW; case-fold text and configured paths, convert `\\` to `/`, and match protected path substrings.

Exact local/example configuration:

```json
{
  "source_roots": ["src", "contracts", "examples/contract-rules.json", "pyproject.toml"],
  "documentation_relevant_patterns": [
    "^src/",
    "^contracts/",
    "^examples/contract-rules\\.json$",
    "^pyproject\\.toml$"
  ],
  "documentation_map": [
    {
      "source_pattern": "^src/adcm/application/",
      "docs": [
        "docs/architecture/modules/application.md",
        "docs/architecture/symbols/application.md",
        "docs/architecture/flows/turn-lifecycle.md"
      ]
    },
    {
      "source_pattern": "^src/adcm/domain/",
      "docs": [
        "docs/architecture/modules/domain.md",
        "docs/architecture/symbols/domain.md"
      ]
    },
    {
      "source_pattern": "^src/adcm/ports/",
      "docs": [
        "docs/architecture/modules/ports.md",
        "docs/architecture/symbols/ports.md",
        "docs/architecture/system-context.md"
      ]
    },
    {
      "source_pattern": "^src/adcm/adapters/",
      "docs": [
        "docs/architecture/modules/adapters.md",
        "docs/architecture/symbols/adapters.md",
        "docs/architecture/system-context.md"
      ]
    },
    {
      "source_pattern": "^src/adcm/config\\.py$",
      "docs": ["docs/architecture/system-context.md"]
    },
    {
      "source_pattern": "^(contracts/|examples/contract-rules\\.json$)",
      "docs": [
        "docs/architecture/modules/contract-schema.md",
        "docs/architecture/system-context.md"
      ]
    },
    {
      "source_pattern": "^pyproject\\.toml$",
      "docs": ["docs/architecture/system-context.md"]
    }
  ],
  "quality_commands": {
    "format_check": [],
    "lint": [],
    "typecheck": [],
    "test": ["python -m pytest -q"],
    "build": []
  },
  "pre_commit_quality_stages": ["format_check", "lint"],
  "pre_push_quality_stages": ["typecheck", "test", "build"],
  "stop_quality_stages": [],
  "strict_stop_gate": true
}
```

Retain the v2 evidence/non-evidence patterns. Set protected paths exactly to:

```json
[
  ".github/hooks/",
  ".github/agents/",
  ".github/prompts/",
  ".github/copilot-instructions.md",
  ".codex/skills/",
  ".vscode/",
  "AGENTS.md",
  "scripts/agent/",
  "githooks/"
]
```

Append these exact case-insensitive approval patterns without removing the supplied v2 patterns:

```json
[
  "\\bRemove-Item\\b(?=[^\\r\\n]*-Recurse\\b)",
  "\\b(?:rd|rmdir)\\b[^\\r\\n]*(?:/s|-s)\\b",
  "\\bdel\\b[^\\r\\n]*(?:/s|-s)\\b",
  "\\bgit\\s+restore\\b",
  "\\bgit\\s+checkout\\s+--(?:\\s|$)"
]
```

No application class, endpoint, event, database object, or runtime schema is added or changed.

## 6. Models, schemas, errors, compatibility, and migrations

- Configuration remains JSON and gains v2 keys for curated-document evidence, non-evidence, mapping, impact report, session state, marker enforcement, and strict stop behavior.
- The freshness marker uses schema version 2 and is regenerated from the verified working tree.
- v1 slash-command names remain compatible; v2 changes their default routing to fast workflows and adds explicit reviewed variants.
- Hook failures remain process exit codes plus JSON hook output. Quality-command failures must remain visible.
- This is a repository tooling migration; there is no application/database migration.

## 7. Tests and quality gates

`tests/test_agent_workflow.py` contains these exact tests:

| Test | Behavior proved |
|---|---|
| `test_required_v2_files_are_installed` | Required new agents, prompts, scripts, both skill copies, and architecture index exist. |
| `test_config_tracks_adcm_sources_and_quality_commands` | Exact source roots, relevant patterns, pytest gate, strict Stop setting, and protected paths are configured. |
| `test_documentation_map_routes_adcm_paths` | `infer_docs` routes application, domain, ports, adapters, schema, example, and pyproject paths to the exact curated docs above. |
| `test_source_files_fail_when_no_configured_root_exists` | `source_files` raises the specified `RuntimeError` and does not fall back to a broad scan. |
| `test_git_detects_working_tree_changes_with_scoped_safe_directory` | A temporary Git repository reports an untracked file through `working_tree_changed_files` without changing global/local Git config. |
| `test_validate_setup_rejects_paths_outside_repository` | Absolute and `..`-escaping paths fail; normal repository-relative paths pass. |
| `test_security_guard_recognizes_mutating_tools` | `apply_patch`, `shell_command`, execute/edit names are true; read/search/list/view names are false. |
| `test_security_guard_normalizes_protected_paths` | Case differences and Windows/POSIX separators still match protected paths; ordinary source reads do not. |
| `test_security_patterns_cover_windows_and_git_worktree_commands` | Recursive PowerShell/CMD deletion, `git restore`, and `git checkout --` match approval rules; ordinary read-only Git commands do not. |

- `python scripts/agent/validate_setup.py`
- `python -m compileall -q scripts/agent`
- Codex `quick_validate.py` against `.codex/skills/repository-knowledge`
- `python scripts/agent/repo_inventory.py`
- `python scripts/agent/doc_impact.py --working-tree --write`
- `python scripts/agent/doc_freshness.py --mark-current --reason "bootstrapped ADCM architecture knowledge and installed agent workflow v2"`
- `python scripts/agent/doc_freshness.py --check --json`
- `python -m pytest -q tests/test_agent_workflow.py`
- `python -m pytest -q` (report any pre-existing failure without weakening tests)
- Final `git -c safe.directory=... diff` and status inspection preserving unrelated changes.

## 8. Implementation order

1. Finalize this contract after one independent review.
2. Copy package files to target locations.
3. Apply ADCM-specific configuration, instructions, skill metadata, and support documentation.
4. Add curated architecture knowledge and configuration tests.
5. Run setup validation, script compilation, skill validation, and focused tests.
6. Generate inventory/impact output, mark verified documentation current, and run freshness plus full tests.
7. Self-review the complete diff and record all failures and deviations.

## 9. Risks, assumptions, and open decisions

- Assumption: both `.github/skills` and `.codex/skills` are desired because the repository currently carries Copilot workflow files while this environment discovers project skills from `.codex/skills`.
- Decision: all helper-script Git reads use a repository-specific command-scoped safe-directory override. This avoids global/local configuration mutation while allowing impact and freshness commands to observe the real worktree.
- Risk: the user-owned schema rename/deletion can make the full test suite fail independently of this migration.
- Risk: strict Stop hooks can block sessions when documentation is stale. Full tests remain a pre-push gate, while Stop quality stages remain empty to avoid repeated full-suite execution at session end.
- Risk: the v2 staged gate verifies that a marker is staged but cannot prove that the marker represents the exact staged tree; this remains a known package limitation.
- Decision: do not install Git hooks automatically because that mutates repository Git configuration beyond placing the requested files.

## 10. Acceptance criteria

- All operational v2 package files exist at their mapped locations and `validate_setup.py` reports `SETUP VALID`.
- ADCM-specific instructions contain no project placeholders.
- Fast and reviewed prompts reference valid installed agents with correct subagent-tool separation.
- Both Copilot and Codex repository-knowledge skills contain required templates; the Codex skill passes `quick_validate.py`.
- Configured source roots and documentation mappings cover ADCM Python, contract/example JSON, and project metadata.
- Curated architecture docs and generated inventory exist; freshness reports `CURRENT` after explicit verification.
- Focused workflow tests pass; full-suite failures, if any, are reported with their pre-existing file context.
- Pre-existing working-tree changes are not overwritten or deleted.

## 11. Symbol change registry

| Status | Path | Symbol/key | Change |
|---|---|---|---|
| EXISTING | `scripts/agent/common.py` | config/source/Git helpers | Replace with v2 behavior. |
| EXISTING | `scripts/agent/common.py` | `run_git` | Add command-scoped repository trust. |
| NEW | `scripts/agent/security_guard.py` | `is_mutating_tool`, `contains_protected_path` | Cover shell/patch tools and normalized protected paths. |
| NEW | `scripts/agent/doc_impact.py` | `infer_docs`, `render_markdown`, `main` | Suggest impacted curated documents. |
| EXISTING | `scripts/agent/doc_freshness.py` | `compare`, `mark_current`, `check_staged` | Upgrade to schema-v2 freshness and evidence checks. |
| NEW | `scripts/agent/setup_workflow.py` | `main` | Initialize local config and inventory. |
| NEW | `scripts/agent/validate_setup.py` | `main` | Validate files, agent references, prompt tools, and config. |
| NEW | `scripts/agent/validate_setup.py` | `is_repo_relative_path` | Reject configured paths outside the repository. |
| EXISTING | `scripts/agent/session_context.py` | `main` | Record per-session source baseline. |
| EXISTING | `scripts/agent/stop_gate.py` | `main` | Gate only source changed in the session. |
| NEW | `.github/agents/feature-fast.agent.md` | `Feature Fast` | Single-agent implementation workflow. |
| NEW | `.github/agents/planner-fast.agent.md` | `Planner Fast` | Single-agent planning workflow. |
| NEW | `.codex/skills/repository-knowledge/` | `repository-knowledge` | Codex-discoverable repository skill. |

## 12. Contract review resolution

- CR-001 resolved: sections 4, 5, and 7 now name every curated document, exact configuration values, helper behavior, and test.
- CR-002 resolved: `run_git` uses command-scoped trust and a temporary-repository test proves worktree detection without persistent Git config.
- CR-003 resolved: exact mutation tokens, path normalization, protected prefixes, approval regexes, and positive/negative tests are specified.

## 13. Implementation deviations

- The reviewed PowerShell pattern placed a word boundary immediately before `-Recurse`. A hyphen is not a word character, so the boundary could never match after whitespace. Focused test evidence required removing that one boundary: `\\bRemove-Item\\b(?=[^\\r\\n]*-Recurse\\b)`. Scope and approval behavior are otherwise unchanged.
