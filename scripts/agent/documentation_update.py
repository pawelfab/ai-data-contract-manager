from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime, timezone

from common import ROOT, current_source_hashes, git_available, load_config, run_git
from doc_freshness import compare, mark_current


def changed_paths_after_commit(config: dict) -> tuple[str | None, list[str]]:
    """Return paths in HEAD; remain usable when a repository export has no Git metadata."""

    if git_available():
        commit = run_git(["rev-parse", "HEAD"])
        changed = run_git(["diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"])
        if commit.returncode == 0 and changed.returncode == 0:
            return commit.stdout.strip(), sorted(
                line.replace("\\", "/") for line in changed.stdout.splitlines() if line.strip()
            )
    return None, sorted(current_source_hashes(config))


def suggested_docs(paths: list[str], config: dict) -> list[str]:
    suggestions: set[str] = set()
    for path in paths:
        for item in config.get("documentation_map", []):
            if re.search(item["source_pattern"], path, flags=re.IGNORECASE):
                suggestions.update(item.get("docs", []))
    return sorted(suggestions)


def render_impact_report(*, commit: str | None, paths: list[str], config: dict) -> str:
    generated_at = datetime.now(timezone.utc).isoformat()
    suggestions = suggested_docs(paths, config)
    lines = [
        "# Generated documentation impact",
        "",
        f"Generated: `{generated_at}`",
        f"Commit: `{commit or 'unavailable; current source inventory used'}`",
        "",
        "> This deterministic review aid does not replace curated architecture or service documentation.",
        "",
        "## Changed source paths",
        "",
    ]
    lines.extend([f"- `{path}`" for path in paths] or ["- No configured source path was detected."])
    lines.extend(["", "## Curated documentation to review", ""])
    lines.extend([f"- `{path}`" for path in suggestions] or ["- No configured documentation mapping matched."])
    lines.extend([
        "",
        "## Commit workflow",
        "",
        "The pre-commit hook requires curated documentation with documentation-relevant code. "
        "The post-commit hook regenerates this report and the repository inventory, then records the source snapshot. "
        "Generated files are left unstaged for review and a subsequent commit.",
        "",
    ])
    return "\n".join(lines)


def generate(config: dict, *, after_commit: bool) -> None:
    inventory = ROOT / "scripts" / "agent" / "repo_inventory.py"
    completed = subprocess.run([sys.executable, str(inventory)], cwd=ROOT, text=True)
    if completed.returncode:
        raise RuntimeError("repository inventory generation failed")

    commit, paths = changed_paths_after_commit(config) if after_commit else (None, compare(config).get("changed", []))
    report_path = ROOT / config["documentation_impact_report"]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_impact_report(commit=commit, paths=paths, config=config), encoding="utf-8")

    reason = "post-commit documentation generation" if after_commit else "manual documentation generation"
    mark_current(config, reason)
    print(f"Wrote {report_path.relative_to(ROOT)}")
    print(f"Updated {config['freshness_file']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate repository documentation aids and update freshness state.")
    parser.add_argument("--after-commit", action="store_true", help="Describe the commit at HEAD.")
    args = parser.parse_args()
    generate(load_config(), after_commit=args.after_commit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
