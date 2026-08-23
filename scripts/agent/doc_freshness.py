from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common import (
    ROOT,
    architecture_dir,
    current_source_hashes,
    documentation_relevant,
    git_available,
    load_config,
    run_git,
    staged_files,
)


def load_state(config: dict[str, Any]) -> dict[str, Any] | None:
    path = ROOT / config["freshness_file"]
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def compare(config: dict[str, Any]) -> dict[str, Any]:
    state = load_state(config)
    current = current_source_hashes(config)
    if not state:
        return {
            "status": "UNKNOWN",
            "reason": "Freshness marker is missing or invalid.",
            "changed": sorted(current),
            "added": sorted(current),
            "deleted": [],
        }
    previous = state.get("source_hashes", {})
    added = sorted(set(current) - set(previous))
    deleted = sorted(set(previous) - set(current))
    modified = sorted(path for path in set(current) & set(previous) if current[path] != previous[path])
    changed = sorted(set(added + deleted + modified))
    return {
        "status": "CURRENT" if not changed else "STALE",
        "reason": "No configured source hash changed." if not changed else "Configured source files changed.",
        "changed": changed,
        "added": added,
        "deleted": deleted,
        "modified": modified,
        "last_marked_at": state.get("marked_at"),
        "last_reason": state.get("reason"),
        "commit": state.get("commit"),
    }


def mark_current(config: dict[str, Any], reason: str) -> dict[str, Any]:
    commit = None
    branch = None
    dirty = None
    if git_available():
        commit_result = run_git(["rev-parse", "HEAD"])
        branch_result = run_git(["branch", "--show-current"])
        status_result = run_git(["status", "--porcelain"])
        commit = commit_result.stdout.strip() if commit_result.returncode == 0 else None
        branch = branch_result.stdout.strip() if branch_result.returncode == 0 else None
        dirty = bool(status_result.stdout.strip())
    payload = {
        "schema_version": 1,
        "marked_at": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "commit": commit,
        "branch": branch,
        "working_tree_dirty": dirty,
        "source_hashes": current_source_hashes(config),
    }
    path = ROOT / config["freshness_file"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def check_staged(config: dict[str, Any]) -> dict[str, Any]:
    files = staged_files()
    relevant_code = [
        p for p in files
        if documentation_relevant(p, config)
        and not p.startswith(config["architecture_docs_dir"].rstrip("/") + "/")
    ]
    evidence_patterns = config.get("documentation_evidence_patterns", [])
    non_evidence_patterns = config.get("documentation_non_evidence_patterns", [])
    docs_changed = [
        p for p in files
        if any(re.search(pattern, p, flags=re.IGNORECASE) for pattern in evidence_patterns)
        and not any(re.search(pattern, p, flags=re.IGNORECASE) for pattern in non_evidence_patterns)
    ]
    required = bool(config.get("require_docs_for_staged_relevant_code", True))
    ok = not required or not relevant_code or bool(docs_changed)
    return {
        "status": "CURRENT" if ok else "STALE",
        "relevant_staged_code": relevant_code,
        "staged_architecture_docs": docs_changed,
        "reason": (
            "No staged documentation-relevant code."
            if not relevant_code else
            "Curated documentation is staged."
            if docs_changed else
            "Documentation-relevant code is staged without curated documentation."
        ),
    }


def print_human(result: dict[str, Any]) -> None:
    print(f"Documentation freshness: {result['status']}")
    print(result.get("reason", ""))
    changed = result.get("changed") or result.get("relevant_staged_code") or []
    if changed:
        print("Relevant changed files:")
        for path in changed[:100]:
            print(f"  - {path}")
    docs = result.get("staged_architecture_docs") or []
    if docs:
        print("Staged architecture documentation:")
        for path in docs[:100]:
            print(f"  - {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check or update architecture documentation freshness.")
    parser.add_argument("--check", action="store_true", help="Compare source hashes with the freshness marker.")
    parser.add_argument("--check-staged", action="store_true", help="Check staged relevant code has staged architecture docs.")
    parser.add_argument("--mark-current", action="store_true", help="Write the current source hashes as documented.")
    parser.add_argument("--reason", default="manual documentation synchronization")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    config = load_config()
    if args.mark_current:
        result = mark_current(config, args.reason)
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.as_json else f"Marked current: {config['freshness_file']}")
        return 0

    result = check_staged(config) if args.check_staged else compare(config)
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_human(result)
    return 0 if result["status"] == "CURRENT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
