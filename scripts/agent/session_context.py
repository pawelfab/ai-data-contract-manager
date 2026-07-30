from __future__ import annotations

from common import hook_output, load_config, read_stdin_json, run_git, git_available
from doc_freshness import compare


def main() -> int:
    read_stdin_json()
    config = load_config()
    result = compare(config)
    branch = "unknown"
    if git_available():
        branch_result = run_git(["branch", "--show-current"])
        if branch_result.returncode == 0 and branch_result.stdout.strip():
            branch = branch_result.stdout.strip()

    changed = result.get("changed", [])
    suffix = ""
    if changed:
        shown = ", ".join(changed[:12])
        suffix = f" Changed source files: {shown}"
        if len(changed) > 12:
            suffix += f" (+{len(changed) - 12} more)."

    context = (
        f"Repository branch: {branch}. "
        f"Architecture documentation freshness: {result['status']}. "
        f"Read AGENTS.md and docs/architecture/README.md before broad repository analysis."
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
