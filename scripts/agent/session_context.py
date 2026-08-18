from __future__ import annotations

import json
import time
from pathlib import Path

from common import (
    current_source_hashes,
    hook_output,
    load_config,
    read_stdin_json,
    run_git,
    git_available,
    session_state_path,
)
from doc_freshness import compare


def cleanup_state(config: dict) -> None:
    directory = Path(__file__).resolve().parents[2] / config.get("session_state_dir", ".agent-state")
    if not directory.exists():
        return
    max_age = int(config.get("session_state_max_age_hours", 168)) * 3600
    now = time.time()
    for path in directory.glob("session-*.json"):
        try:
            if now - path.stat().st_mtime > max_age:
                path.unlink()
        except OSError:
            pass


def main() -> int:
    payload = read_stdin_json()
    config = load_config()
    cleanup_state(config)

    freshness = compare(config)
    branch = "unknown"
    if git_available():
        branch_result = run_git(["branch", "--show-current"])
        if branch_result.returncode == 0 and branch_result.stdout.strip():
            branch = branch_result.stdout.strip()

    session_id = str(payload.get("session_id") or payload.get("sessionId") or "unknown")
    state = {
        "session_id": session_id,
        "started_at_epoch": time.time(),
        "branch": branch,
        "baseline_freshness": freshness,
        "baseline_source_hashes": current_source_hashes(config),
    }
    path = session_state_path(config, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    changed = freshness.get("changed", [])
    suffix = ""
    if changed:
        shown = ", ".join(changed[:12])
        suffix = f" Changed since last documentation sync: {shown}"
        if len(changed) > 12:
            suffix += f" (+{len(changed) - 12} more)."

    context = (
        f"Repository branch: {branch}. "
        f"Architecture documentation freshness at session start: {freshness['status']}. "
        "Use fast slash commands for ordinary bounded work and reviewed commands for high-risk changes. "
        "After source edits, update curated architecture docs, regenerate inventory, and mark freshness current."
        f"{suffix}"
    )
    hook_output(
        specific={
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
