from __future__ import annotations

from common import hook_output, load_config, read_stdin_json
from doc_freshness import compare
from quality_gate import run_stages


def main() -> int:
    read_stdin_json()
    config = load_config()
    freshness = compare(config)
    quality_stages = config.get("stop_quality_stages", [])
    quality_ok, results = run_stages(quality_stages, config) if quality_stages else (True, [])

    messages: list[str] = []
    if freshness["status"] != "CURRENT":
        changed = freshness.get("changed", [])
        shown = ", ".join(changed[:10])
        messages.append(
            f"Architecture documentation is {freshness['status']}. "
            f"Run Docs Updater before declaring a code-changing task complete. Changed: {shown or 'unknown'}."
        )
    if not quality_ok:
        failed = [item["command"] for item in results if item["returncode"] != 0]
        messages.append("Quality gate failed: " + "; ".join(failed))

    strict = bool(config.get("strict_stop_gate", False))
    should_stop = strict and bool(messages)
    hook_output(
        continue_=not should_stop,
        stop_reason=" | ".join(messages) if should_stop else None,
        system_message=" | ".join(messages) if messages else None,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
