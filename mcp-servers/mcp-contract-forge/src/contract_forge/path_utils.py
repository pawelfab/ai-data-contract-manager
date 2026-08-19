from __future__ import annotations

from copy import deepcopy
from typing import Any

from .models import AppliedValue, Origin, can_replace

_MISSING = object()


def split_path(path: str) -> list[str]:
    return [p for p in path.split(".") if p]


def get_path(data: Any, path: str, default: Any = _MISSING) -> Any:
    current = data
    for part in split_path(path):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            if default is _MISSING:
                raise KeyError(path)
            return default
    return current


def has_path(data: Any, path: str) -> bool:
    try:
        get_path(data, path)
        return True
    except KeyError:
        return False


def set_path(data: dict[str, Any], path: str, value: Any) -> None:
    parts = split_path(path)
    if not parts:
        raise ValueError("path cannot be empty")
    current: Any = data
    for part in parts[:-1]:
        if isinstance(current, dict):
            current = current.setdefault(part, {})
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            raise TypeError(f"Cannot descend through value at {part!r} for {path!r}")
    leaf = parts[-1]
    if isinstance(current, dict):
        current[leaf] = deepcopy(value)
        return
    if isinstance(current, list) and leaf.isdigit() and int(leaf) < len(current):
        current[int(leaf)] = deepcopy(value)
        return
    raise TypeError(f"Cannot set {path!r} on current value")


def write_value(
    contract: dict[str, Any],
    origins: dict[str, Origin],
    path: str,
    value: Any,
    origin: Origin,
    *,
    rule_id: str | None = None,
) -> AppliedValue | None:
    """Apply one value through the central origin-precedence and provenance rule."""
    current_origin = origins.get(path) if has_path(contract, path) else None
    if not can_replace(current_origin, origin):
        return None
    set_path(contract, path, value)
    origins[path] = origin
    return AppliedValue(
        path=path,
        value=deepcopy(value),
        origin=origin,
        rule_id=rule_id,
    )


def delete_path(data: dict[str, Any], path: str) -> None:
    parts = split_path(path)
    if not parts:
        return
    current: Any = data
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            return
        current = current[part]
    if isinstance(current, dict):
        current.pop(parts[-1], None)
