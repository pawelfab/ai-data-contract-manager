from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from common import (
    ROOT,
    documentation_relevant,
    load_config,
    staged_files,
    working_tree_changed_files,
)
from doc_freshness import compare


def changed_paths(args: argparse.Namespace, config: dict[str, Any]) -> list[str]:
    if args.staged:
        return staged_files()
    if args.since_marker:
        return compare(config).get("changed", [])
    return working_tree_changed_files()


def format_docs(template: str, match: re.Match[str]) -> str:
    values = match.groupdict()
    try:
        return template.format(**values)
    except KeyError:
        return template


def infer_docs(paths: list[str], config: dict[str, Any]) -> dict[str, Any]:
    relevant = [path for path in paths if documentation_relevant(path, config)]
    mapping = config.get("documentation_map", [])
    suggestions: dict[str, set[str]] = {}
    unmatched: list[str] = []

    for path in relevant:
        docs: set[str] = set()
        for rule in mapping:
            pattern = rule.get("source_pattern", "")
            match = re.search(pattern, path, flags=re.IGNORECASE)
            if not match:
                continue
            for template in rule.get("docs", []):
                docs.add(format_docs(template, match))
        if not docs:
            unmatched.append(path)
            docs.add("docs/architecture/README.md")
        suggestions[path] = docs

    all_docs = sorted({doc for docs in suggestions.values() for doc in docs})
    return {
        "changed_paths": paths,
        "documentation_relevant_paths": relevant,
        "suggested_docs": all_docs,
        "by_source": {path: sorted(docs) for path, docs in suggestions.items()},
        "unmatched_paths": unmatched,
        "note": "Suggestions are navigation hints. Verify actual behavior, callers, flows, and documentation scope before editing.",
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Generated documentation impact",
        "",
        "> Mechanical suggestion only. Verify against code, tests, callers, and existing architecture documents.",
        "",
        "## Documentation-relevant changed paths",
        "",
    ]
    paths = report["documentation_relevant_paths"]
    lines.extend([f"- `{path}`" for path in paths] or ["- None detected."])
    lines.extend(["", "## Suggested curated documents", ""])
    lines.extend([f"- `{path}`" for path in report["suggested_docs"]] or ["- None."])
    lines.extend(["", "## Mapping", ""])
    for source, docs in report["by_source"].items():
        lines.append(f"### `{source}`")
        lines.extend([f"- `{doc}`" for doc in docs])
        lines.append("")
    if report["unmatched_paths"]:
        lines.extend(["## Paths requiring manual mapping", ""])
        lines.extend([f"- `{path}`" for path in report["unmatched_paths"]])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Suggest architecture documentation affected by repository changes.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--working-tree", action="store_true", help="Use current staged, unstaged, and untracked changes (default).")
    group.add_argument("--staged", action="store_true", help="Use staged changes only.")
    group.add_argument("--since-marker", action="store_true", help="Use source changes since the freshness marker.")
    parser.add_argument("--write", action="store_true", help="Write the generated Markdown impact report.")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    config = load_config()
    paths = changed_paths(args, config)
    report = infer_docs(paths, config)

    if args.write:
        target = ROOT / config["documentation_impact_report"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_markdown(report), encoding="utf-8")
        report["written_to"] = target.relative_to(ROOT).as_posix()

    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(report), end="")
        if report.get("written_to"):
            print(f"Wrote {report['written_to']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
