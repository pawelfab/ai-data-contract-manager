from __future__ import annotations

import json
import re
from typing import Any

from common import hook_output, load_config, read_stdin_json


MUTATING_TOOL_TOKENS = (
    "edit",
    "create",
    "delete",
    "write",
    "terminal",
    "execute",
    "shell",
    "command",
    "apply_patch",
    "patch",
    "replace",
    "insert",
)


def flatten(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(f"{key} {flatten(val)}" for key, val in value.items())
    if isinstance(value, list):
        return " ".join(flatten(item) for item in value)
    return str(value)


def is_mutating_tool(tool_name: str) -> bool:
    normalized = tool_name.casefold()
    return any(token in normalized for token in MUTATING_TOOL_TOKENS)


def contains_protected_path(text: str, paths: list[str]) -> bool:
    normalized = text.replace("\\", "/").casefold()
    return any(path.replace("\\", "/").casefold() in normalized for path in paths)


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

    if contains_protected_path(text, config.get("protected_agent_paths", [])):
        if is_mutating_tool(tool_name):
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
