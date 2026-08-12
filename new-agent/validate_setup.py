from __future__ import annotations

import json
import re
from pathlib import Path

from common import ROOT, load_config


REQUIRED_FILES = [
    "AGENTS.md",
    ".github/copilot-instructions.md",
    ".github/agents/planner-fast.agent.md",
    ".github/agents/feature-fast.agent.md",
    ".github/agents/feature-coordinator.agent.md",
    ".github/prompts/plan-change.prompt.md",
    ".github/prompts/plan-change-reviewed.prompt.md",
    ".github/prompts/implement-change.prompt.md",
    ".github/prompts/implement-change-reviewed.prompt.md",
    ".github/hooks/agent-workflow.json",
    "scripts/agent/config.example.json",
    "scripts/agent/doc_freshness.py",
    "scripts/agent/doc_impact.py",
]


def frontmatter(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    return match.group(1) if match else ""


def field_value(header: str, name: str) -> str | None:
    match = re.search(rf"^{re.escape(name)}:\s*(.+)$", header, flags=re.M)
    return match.group(1).strip() if match else None


def list_field(header: str, name: str) -> list[str]:
    raw = field_value(header, name)
    if raw and raw.startswith("["):
        return re.findall(r"['\"]([^'\"]+)['\"]", raw)
    block = re.search(rf"^{re.escape(name)}:\s*\n((?:\s+-\s+.+\n?)+)", header, flags=re.M)
    if not block:
        return []
    return [line.split("-", 1)[1].strip().strip("'\"") for line in block.group(1).splitlines()]


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    for relative in REQUIRED_FILES:
        if not (ROOT / relative).exists():
            errors.append(f"Missing required file: {relative}")

    try:
        config = load_config()
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"Invalid agent config: {exc}")
        config = {}

    for key in [
        "source_roots",
        "architecture_docs_dir",
        "freshness_file",
        "documentation_evidence_patterns",
        "quality_commands",
    ]:
        if key not in config:
            errors.append(f"Missing config key: {key}")

    agents: dict[str, Path] = {}
    for path in (ROOT / ".github" / "agents").glob("*.agent.md"):
        header = frontmatter(path)
        name = field_value(header, "name") or path.stem
        agents[name.strip("'\"")] = path

    for path in (ROOT / ".github" / "prompts").glob("*.prompt.md"):
        header = frontmatter(path)
        agent = field_value(header, "agent")
        if agent and agent.strip("'\"") not in agents and agent.strip("'\"") not in {"ask", "agent", "plan"}:
            errors.append(f"{path.relative_to(ROOT)} references unknown agent: {agent}")

    fast_prompts = [
        ROOT / ".github/prompts/plan-change.prompt.md",
        ROOT / ".github/prompts/plan-change-preview.prompt.md",
        ROOT / ".github/prompts/implement-change.prompt.md",
    ]
    for path in fast_prompts:
        if path.exists() and "agent" in list_field(frontmatter(path), "tools"):
            errors.append(f"Fast prompt exposes subagent tool: {path.relative_to(ROOT)}")

    reviewed_prompts = [
        ROOT / ".github/prompts/plan-change-reviewed.prompt.md",
        ROOT / ".github/prompts/implement-change-reviewed.prompt.md",
        ROOT / ".github/prompts/review-current-change.prompt.md",
    ]
    for path in reviewed_prompts:
        if path.exists() and "agent" not in list_field(frontmatter(path), "tools"):
            errors.append(f"Reviewed prompt lacks subagent tool: {path.relative_to(ROOT)}")

    local_config = ROOT / "scripts/agent/config.json"
    if not local_config.exists():
        warnings.append("scripts/agent/config.json is missing; config.example.json is being used.")

    if not any((ROOT / root).exists() for root in config.get("source_roots", [])):
        warnings.append("None of the configured source_roots exists yet; adapt scripts/agent/config.json.")

    if errors:
        print("SETUP INVALID")
        for item in errors:
            print(f"ERROR: {item}")
    else:
        print("SETUP VALID")

    for item in warnings:
        print(f"WARNING: {item}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
