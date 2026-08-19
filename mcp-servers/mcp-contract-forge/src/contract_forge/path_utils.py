from __future__ import annotations

from copy import deepcopy
from typing import Any

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
        else:
            raise TypeError(f"Cannot descend through non-object at {part!r} for {path!r}")
    if not isinstance(current, dict):
        raise TypeError(f"Cannot set {path!r} on non-object")
    current[parts[-1]] = deepcopy(value)


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
