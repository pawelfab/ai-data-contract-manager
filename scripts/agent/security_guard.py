from __future__ import annotations

import json
import re
from typing import Any

from common import hook_output, load_config, read_stdin_json


def flatten(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(f"{key} {flatten(val)}" for key, val in value.items())
    if isinstance(value, list):
        return " ".join(flatten(item) for item in value)
    return str(value)


def main() -> int:
    payload = read_stdin_json()
    config = load_config()
    tool_name = str(payload.get("tool_name") or payload.get("toolName") or "")
    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    text = flatten(tool_input)

    for pattern in config.get("deny_command_patterns", []):
        if re.search(pattern, text, flags=re.IGNORECASE):
            hook_output(specific={
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"Blocked by repository safety rule: {pattern}",
            })
            return 0

    for pattern in config.get("approval_command_patterns", []):
        if re.search(pattern, text, flags=re.IGNORECASE):
            hook_output(specific={
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": f"Sensitive operation requires approval: {pattern}",
            })
            return 0

    normalized = text.replace("\\", "/")
    if any(path in normalized for path in config.get("protected_agent_paths", [])):
        lower_tool = tool_name.lower()
        if any(word in lower_tool for word in ("edit", "create", "delete", "write", "terminal", "execute")):
            hook_output(specific={
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": "Changes to agent control, hook, or safety files require manual approval.",
            })
            return 0

    hook_output(specific={
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow",
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
