from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from typing import Any

from common import (
    ROOT,
    current_architecture_doc_hashes,
    current_source_hashes,
    documentation_relevant,
    git_available,
    hash_delta,
    load_config,
    matches_any,
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
            "modified": [],
        }
    delta = hash_delta(state.get("source_hashes", {}), current)
    return {
        "status": "CURRENT" if not delta["changed"] else "STALE",
        "reason": "No configured source hash changed." if not delta["changed"] else "Configured source files changed.",
        **delta,
        "last_marked_at": state.get("marked_at"),
        "last_reason": state.get("reason"),
        "commit": state.get("commit"),
        "branch": state.get("branch"),
        "no_doc_change_exception": bool(state.get("no_doc_change_exception", False)),
    }


def mark_current(config: dict[str, Any], reason: str, allow_no_doc_change: bool) -> tuple[bool, dict[str, Any]]:
    previous = load_state(config)
    source_hashes = current_source_hashes(config)
    doc_hashes = current_architecture_doc_hashes(config)

    source_delta = hash_delta(previous.get("source_hashes", {}) if previous else {}, source_hashes)
    doc_delta = hash_delta(previous.get("curated_doc_hashes", {}) if previous else {}, doc_hashes)

    source_changed = bool(previous and source_delta["changed"])
    docs_changed = bool(previous and doc_delta["changed"])

    if source_changed and not docs_changed and not allow_no_doc_change:
        return False, {
            "status": "REFUSED",
            "reason": (
                "Configured source changed but no curated architecture documentation changed. "
                "Update relevant docs, or explicitly use --allow-no-doc-change with a specific rationale."
            ),
            "source_changed": source_delta["changed"],
            "curated_docs_changed": [],
        }

    normalized_reason = reason.strip()
    if allow_no_doc_change and source_changed and len(normalized_reason) < 24:
        return False, {
            "status": "REFUSED",
            "reason": "The no-documentation-impact exception requires a specific rationale of at least 24 characters.",
            "source_changed": source_delta["changed"],
        }

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
        "schema_version": 2,
        "marked_at": datetime.now(timezone.utc).isoformat(),
        "reason": normalized_reason,
        "commit": commit,
        "branch": branch,
        "working_tree_dirty": dirty,
        "no_doc_change_exception": bool(allow_no_doc_change and source_changed and not docs_changed),
        "source_delta_at_mark": source_delta,
        "curated_doc_delta_at_mark": doc_delta,
        "source_hashes": source_hashes,
        "curated_doc_hashes": doc_hashes,
    }
    path = ROOT / config["freshness_file"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True, payload


def check_staged(config: dict[str, Any]) -> dict[str, Any]:
    files = staged_files()
    doc_prefix = config["architecture_docs_dir"].rstrip("/") + "/"
    freshness_path = config["freshness_file"].replace("\\", "/")

    relevant_code = [
        path for path in files
        if documentation_relevant(path, config) and not path.startswith(doc_prefix)
    ]
    evidence_patterns = config.get("documentation_evidence_patterns", [])
    non_evidence_patterns = config.get("documentation_non_evidence_patterns", [])
    curated_docs = [
        path for path in files
        if matches_any(path, evidence_patterns) and not matches_any(path, non_evidence_patterns)
    ]
    marker_staged = freshness_path in files
    state = load_state(config) or {}
    explicit_no_impact = marker_staged and bool(state.get("no_doc_change_exception", False))

    require_docs = bool(config.get("require_docs_for_staged_relevant_code", True))
    require_marker = bool(config.get("require_freshness_marker_for_staged_relevant_code", True))

    docs_ok = (not require_docs) or (not relevant_code) or bool(curated_docs) or explicit_no_impact
    marker_ok = (not require_marker) or (not relevant_code) or marker_staged
    ok = docs_ok and marker_ok

    reasons: list[str] = []
    if not relevant_code:
        reasons.append("No staged documentation-relevant source code.")
    else:
        if curated_docs:
            reasons.append("Curated architecture documentation is staged.")
        elif explicit_no_impact:
            reasons.append("A staged explicit no-documentation-impact exception is present.")
        elif require_docs:
            reasons.append("Relevant source is staged without curated architecture documentation.")
        if marker_staged:
            reasons.append("The freshness marker is staged.")
        elif require_marker:
            reasons.append("The freshness marker is not staged.")

    return {
        "status": "CURRENT" if ok else "STALE",
        "relevant_staged_code": relevant_code,
        "staged_curated_docs": curated_docs,
        "freshness_marker_staged": marker_staged,
        "explicit_no_doc_impact": explicit_no_impact,
        "reason": " ".join(reasons),
    }


def print_human(result: dict[str, Any]) -> None:
    print(f"Documentation freshness: {result['status']}")
    print(result.get("reason", ""))
    changed = result.get("changed") or result.get("relevant_staged_code") or []
    if changed:
        print("Relevant changed files:")
        for path in changed[:100]:
            print(f"  - {path}")
    docs = result.get("staged_curated_docs") or []
    if docs:
        print("Staged curated architecture documentation:")
        for path in docs[:100]:
            print(f"  - {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check or update architecture documentation freshness.")
    parser.add_argument("--check", action="store_true", help="Compare source hashes with the freshness marker.")
    parser.add_argument("--check-staged", action="store_true", help="Check staged code, curated docs, and freshness marker.")
    parser.add_argument("--mark-current", action="store_true", help="Write current source and documentation hashes.")
    parser.add_argument("--allow-no-doc-change", action="store_true", help="Explicitly acknowledge that changed source has no documentation impact.")
    parser.add_argument("--reason", default="manual documentation synchronization")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    config = load_config()
    if args.mark_current:
        ok, result = mark_current(config, args.reason, args.allow_no_doc_change)
        if args.as_json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif ok:
            print(f"Marked current: {config['freshness_file']}")
            if result.get("no_doc_change_exception"):
                print("Recorded explicit no-documentation-impact exception.")
        else:
            print_human(result)
        return 0 if ok else 2

    result = check_staged(config) if args.check_staged else compare(config)
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_human(result)
    return 0 if result["status"] == "CURRENT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
