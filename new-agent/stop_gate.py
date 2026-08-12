from __future__ import annotations

import json

from common import (
    current_source_hashes,
    hash_delta,
    hook_output,
    load_config,
    read_stdin_json,
    session_state_path,
)
from doc_freshness import compare
from quality_gate import run_stages


def load_session_state(config: dict, session_id: str) -> dict | None:
    path = session_state_path(config, session_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def main() -> int:
    payload = read_stdin_json()
    config = load_config()
    session_id = str(payload.get("session_id") or payload.get("sessionId") or "unknown")
    state = load_session_state(config, session_id)

    changed_in_session: list[str] = []
    if state:
        delta = hash_delta(state.get("baseline_source_hashes", {}), current_source_hashes(config))
        changed_in_session = delta["changed"]

    freshness = compare(config)
    source_changed = bool(changed_in_session)
    quality_stages = config.get("stop_quality_stages", []) if source_changed else []
    quality_ok, results = run_stages(quality_stages, config) if quality_stages else (True, [])

    messages: list[str] = []
    blocking: list[str] = []

    if source_changed and freshness["status"] != "CURRENT":
        shown = ", ".join(changed_in_session[:10])
        message = (
            "This session changed configured source files, but architecture documentation is "
            f"{freshness['status']}. Update curated docs, regenerate inventory, and mark freshness current. "
            f"Session source changes: {shown or 'unknown'}."
        )
        messages.append(message)
        blocking.append(message)
    elif not source_changed and freshness["status"] != "CURRENT":
        messages.append(
            f"Architecture documentation was already {freshness['status']} or became stale outside this session. "
            "Do not treat it as confirmed without bounded code verification."
        )

    if source_changed and not quality_ok:
        failed = [item["command"] for item in results if item["returncode"] != 0]
        message = "Configured Stop quality gate failed: " + "; ".join(failed)
        messages.append(message)
        blocking.append(message)

    strict = bool(config.get("strict_stop_gate", True))
    should_stop = strict and bool(blocking)
    hook_output(
        continue_=not should_stop,
        stop_reason=" | ".join(blocking) if should_stop else None,
        system_message=" | ".join(messages) if messages else None,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
