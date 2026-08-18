from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).parents[1]
AGENT_SCRIPTS = REPOSITORY_ROOT / "scripts" / "agent"
sys.path.insert(0, str(AGENT_SCRIPTS))

import common  # noqa: E402
import doc_impact  # noqa: E402
import security_guard  # noqa: E402
import validate_setup  # noqa: E402


def load_config() -> dict:
    return json.loads((AGENT_SCRIPTS / "config.example.json").read_text(encoding="utf-8"))


def test_required_v2_files_are_installed() -> None:
    required = [
        ".github/agents/feature-fast.agent.md",
        ".github/agents/planner-fast.agent.md",
        ".github/prompts/implement-change-reviewed.prompt.md",
        ".github/prompts/plan-change-preview.prompt.md",
        ".github/prompts/plan-change-reviewed.prompt.md",
        ".github/prompts/review-current-change.prompt.md",
        ".github/skills/repository-knowledge/SKILL.md",
        ".codex/skills/repository-knowledge/SKILL.md",
        ".codex/skills/repository-knowledge/agents/openai.yaml",
        "scripts/agent/doc_impact.py",
        "scripts/agent/setup_workflow.py",
        "scripts/agent/validate_setup.py",
        "docs/architecture/README.md",
    ]
    assert [path for path in required if not (REPOSITORY_ROOT / path).is_file()] == []


def test_config_tracks_adcm_sources_and_quality_commands() -> None:
    config = load_config()
    assert config["source_roots"] == [
        "src",
        "contracts",
        "examples/contract-rules.json",
        "pyproject.toml",
    ]
    assert config["documentation_relevant_patterns"] == [
        "^src/",
        "^contracts/",
        r"^examples/contract-rules\.json$",
        r"^pyproject\.toml$",
    ]
    assert config["quality_commands"]["test"] == ["python -m pytest -q"]
    assert config["stop_quality_stages"] == []
    assert config["strict_stop_gate"] is True
    assert {
        ".github/prompts/",
        ".codex/skills/",
        ".vscode/",
    }.issubset(config["protected_agent_paths"])


def test_documentation_map_routes_adcm_paths() -> None:
    paths = [
        "src/adcm/application/chat_service.py",
        "src/adcm/domain/models.py",
        "src/adcm/ports/contract_forge.py",
        "src/adcm/adapters/mcp/mock_contract_forge.py",
        "src/adcm/config.py",
        "contracts/contract.json",
        "examples/contract-rules.json",
        "pyproject.toml",
    ]
    report = doc_impact.infer_docs(paths, load_config())
    assert report["unmatched_paths"] == []
    assert report["by_source"][paths[0]] == [
        "docs/architecture/flows/turn-lifecycle.md",
        "docs/architecture/modules/application.md",
        "docs/architecture/symbols/application.md",
    ]
    assert "docs/architecture/modules/domain.md" in report["by_source"][paths[1]]
    assert "docs/architecture/modules/ports.md" in report["by_source"][paths[2]]
    assert "docs/architecture/modules/adapters.md" in report["by_source"][paths[3]]
    assert report["by_source"][paths[4]] == ["docs/architecture/system-context.md"]
    assert "docs/architecture/modules/contract-schema.md" in report["by_source"][paths[5]]
    assert "docs/architecture/modules/contract-schema.md" in report["by_source"][paths[6]]
    assert report["by_source"][paths[7]] == ["docs/architecture/system-context.md"]


def test_source_files_fail_when_no_configured_root_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(common, "ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="None of the configured source_roots exists"):
        common.source_files(
            {
                "source_roots": ["missing"],
                "source_extensions": [".py"],
                "exclude_dirs": [],
            }
        )


def test_git_detects_working_tree_changes_with_scoped_safe_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "change.py").write_text("value = 1\n", encoding="utf-8")
    monkeypatch.setattr(common, "ROOT", tmp_path)

    assert common.git_available() is True
    assert common.working_tree_changed_files() == ["change.py"]
    assert "safe.directory" not in (tmp_path / ".git" / "config").read_text(encoding="utf-8")


def test_validate_setup_rejects_paths_outside_repository() -> None:
    assert validate_setup.is_repo_relative_path("docs/architecture/.freshness.json") is True
    assert validate_setup.is_repo_relative_path("../outside.json") is False
    assert validate_setup.is_repo_relative_path("C:/outside.json") is False
    assert validate_setup.is_repo_relative_path("") is False


def test_security_guard_recognizes_mutating_tools() -> None:
    for tool in ["apply_patch", "shell_command", "execute", "file_edit", "replace_text"]:
        assert security_guard.is_mutating_tool(tool) is True
    for tool in ["read", "search", "list_files", "view_image"]:
        assert security_guard.is_mutating_tool(tool) is False


def test_security_guard_normalizes_protected_paths() -> None:
    protected = [".github/prompts/", ".codex/skills/", "scripts/agent/"]
    assert security_guard.contains_protected_path(
        r"WRITE .GITHUB\PROMPTS\plan-change.prompt.md", protected
    )
    assert security_guard.contains_protected_path(
        "edit .codex/skills/repository-knowledge/SKILL.md", protected
    )
    assert not security_guard.contains_protected_path("read src/adcm/domain/models.py", protected)


def test_security_patterns_cover_windows_and_git_worktree_commands() -> None:
    patterns = [re.compile(pattern, re.IGNORECASE) for pattern in load_config()["approval_command_patterns"]]
    sensitive = [
        r"Remove-Item C:\temp\work -Recurse -Force",
        r"rmdir /s C:\temp\work",
        r"del /s C:\temp\work\*",
        "git restore src/adcm/domain/models.py",
        "git checkout -- src/adcm/domain/models.py",
    ]
    for command in sensitive:
        assert any(pattern.search(command) for pattern in patterns), command
    assert not any(pattern.search("git status --short") for pattern in patterns)
