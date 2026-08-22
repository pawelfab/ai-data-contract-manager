from __future__ import annotations

from copy import deepcopy
from typing import Any


class JsonPointerError(ValueError):
    pass


def _parts(pointer: str) -> list[str]:
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise JsonPointerError(f"Not a JSON Pointer: {pointer}")
    return [p.replace("~1", "/").replace("~0", "~") for p in pointer[1:].split("/")]


def set_pointer(document: dict[str, Any], pointer: str, value: Any) -> dict[str, Any]:
    out = deepcopy(document)
    parts = _parts(pointer)
    if not parts:
        if not isinstance(value, dict):
            raise JsonPointerError("Root must be object")
        return deepcopy(value)

    cur: Any = out
    traversed: list[str] = []
    for i, part in enumerate(parts[:-1]):
        nxt = parts[i + 1]
        wants_list = nxt.isdigit()
        traversed.append(part)
        prefix = "/" + "/".join(_escape(x) for x in traversed)

        if isinstance(cur, list):
            if not part.isdigit():
                raise JsonPointerError(f"Cannot set {pointer}: {prefix} is not a valid list index")
            idx = int(part)
            while len(cur) <= idx:
                cur.append([] if wants_list else {})
            if cur[idx] is None:
                cur[idx] = [] if wants_list else {}
            elif not isinstance(cur[idx], (dict, list)):
                raise JsonPointerError(
                    f"Cannot set {pointer}: intermediate path {prefix} contains scalar value {cur[idx]!r}"
                )
            cur = cur[idx]
        elif isinstance(cur, dict):
            if part not in cur or cur[part] is None:
                cur[part] = [] if wants_list else {}
            elif not isinstance(cur[part], (dict, list)):
                raise JsonPointerError(
                    f"Cannot set {pointer}: intermediate path {prefix} contains scalar value {cur[part]!r}"
                )
            cur = cur[part]
        else:
            raise JsonPointerError(
                f"Cannot set {pointer}: intermediate path {prefix} contains scalar value {cur!r}"
            )

    last = parts[-1]
    if isinstance(cur, list):
        if not last.isdigit():
            raise JsonPointerError(f"Cannot set {pointer}: final segment must be a list index")
        idx = int(last)
        while len(cur) <= idx:
            cur.append(None)
        cur[idx] = deepcopy(value)
    elif isinstance(cur, dict):
        cur[last] = deepcopy(value)
    else:
        prefix = "/" + "/".join(_escape(x) for x in parts[:-1])
        raise JsonPointerError(
            f"Cannot set {pointer}: intermediate path {prefix} contains scalar value {cur!r}"
        )
    return out


def get_pointer(document: Any, pointer: str, default: Any = None) -> Any:
    cur = document
    try:
        for part in _parts(pointer):
            cur = cur[int(part)] if isinstance(cur, list) else cur[part]
        return cur
    except (KeyError, IndexError, TypeError, ValueError):
        return default


def exists_pointer(document: Any, pointer: str) -> bool:
    marker = object()
    return get_pointer(document, pointer, marker) is not marker


def delete_pointer(document: dict[str, Any], pointer: str) -> dict[str, Any]:
    out = deepcopy(document)
    parts = _parts(pointer)
    if not parts:
        return {}
    cur: Any = out
    try:
        for part in parts[:-1]:
            cur = cur[int(part)] if isinstance(cur, list) else cur[part]
        last = parts[-1]
        if isinstance(cur, list):
            cur.pop(int(last))
        else:
            cur.pop(last, None)
    except (KeyError, IndexError, TypeError, ValueError):
        pass
    return out


def _escape(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")
