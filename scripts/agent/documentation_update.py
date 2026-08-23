from __future__ import annotations

import argparse
import re

from common import (
    ROOT,
    current_source_hashes,
    documentation_relevant,
    load_config,
    run_git,
    source_snapshot_id,
    staged_files,
    staged_source_hashes,
)
from doc_freshness import compare, mark_current, mark_staged
from repo_inventory import generate as generate_inventory


GENERATED_ARTIFACTS = (
    "docs/generated/repository-inventory.json",
    "docs/generated/repository-map.md",
    "docs/generated/documentation-impact.md",
    "docs/.freshness.json",
)


def suggested_docs(paths: list[str], config: dict) -> list[str]:
    suggestions: set[str] = set()
    for path in paths:
        for item in config.get("documentation_map", []):
            if re.search(item["source_pattern"], path, flags=re.IGNORECASE):
                suggestions.update(item.get("docs", []))
    return sorted(suggestions)


def render_impact_report(*, paths: list[str], snapshot_id: str, staged: bool, config: dict) -> str:
    suggestions = suggested_docs(paths, config)
    source = "staged Git index" if staged else "working tree"
    lines = [
        "# Generated documentation impact",
        "",
        f"Source snapshot: `{snapshot_id}`",
        f"Input: `{source}`",
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
        "When documentation-relevant source is staged, the pre-commit hook generates these artifacts "
        "from the staged Git index and stages them in the same commit. "
        "The post-commit hook does not modify the working tree.",
        "",
    ])
    return "\n".join(lines)


def has_staged_documentation_relevant_source(config: dict) -> bool:
    return any(documentation_relevant(path, config) for path in staged_files())


def staged_change_paths() -> list[str]:
    return [path for path in staged_files() if path not in GENERATED_ARTIFACTS]


def stage_generated_artifacts() -> None:
    result = run_git(["add", "--", *GENERATED_ARTIFACTS])
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Unable to stage generated documentation.")


def generate(config: dict, *, staged: bool = False) -> bool:
    if staged:
        if not has_staged_documentation_relevant_source(config):
            print("No documentation-relevant source changes are staged; generated documentation is unchanged.")
            return False
        source_hashes = staged_source_hashes(config)
        paths = staged_change_paths()
    else:
        freshness = compare(config)
        if freshness["status"] == "CURRENT":
            print("Documentation freshness is current; generated documentation is unchanged.")
            return False
        source_hashes = current_source_hashes(config)
        paths = freshness["changed"]

    snapshot_id = source_snapshot_id(source_hashes)
    generate_inventory(config, staged=staged)
    report_path = ROOT / config["documentation_impact_report"]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        render_impact_report(paths=paths, snapshot_id=snapshot_id, staged=staged, config=config),
        encoding="utf-8",
    )

    reason = "pre-commit staged documentation generation" if staged else "manual documentation generation"
    if staged:
        mark_staged(config, reason)
        stage_generated_artifacts()
    else:
        mark_current(config, reason)
    print(f"Wrote {report_path.relative_to(ROOT)}")
    print(f"Updated {config['freshness_file']}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic repository documentation aids.")
    parser.add_argument("--staged", action="store_true", help="Generate from the staged Git index and stage outputs.")
    args = parser.parse_args()
    generate(load_config(), staged=args.staged)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
