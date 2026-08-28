from __future__ import annotations

from typing import Any


class JsonPointerError(ValueError):
    pass


def _tokens(path: str) -> list[str]:
    if path == "":
        return []
    if not path.startswith("/"):
        raise JsonPointerError(f"invalid JSON Pointer: {path!r}")
    return [part.replace("~1", "/").replace("~0", "~") for part in path[1:].split("/")]


def _index(token: str) -> int:
    if token == "-":
        raise JsonPointerError("'-' is valid only for add at the final list token")
    try:
        value = int(token)
    except ValueError as exc:
        raise JsonPointerError(f"invalid list index {token!r}") from exc
    if value < 0:
        raise JsonPointerError("negative list indexes are not supported")
    return value


def get(document: Any, path: str) -> Any:
    node = document
    for token in _tokens(path):
        if isinstance(node, dict):
            if token not in node:
                raise KeyError(path)
            node = node[token]
        elif isinstance(node, list):
            idx = _index(token)
            if idx >= len(node):
                raise KeyError(path)
            node = node[idx]
        else:
            raise KeyError(path)
    return node


def exists(document: Any, path: str) -> bool:
    try:
        get(document, path)
        return True
    except (KeyError, JsonPointerError, TypeError):
        return False


def parent_and_token(document: Any, path: str) -> tuple[Any, str]:
    tokens = _tokens(path)
    if not tokens:
        raise JsonPointerError("root mutation is not supported in baseline")
    node = document
    for token in tokens[:-1]:
        if isinstance(node, dict):
            if token not in node:
                node[token] = {}
            node = node[token]
        elif isinstance(node, list):
            idx = _index(token)
            if idx >= len(node):
                raise JsonPointerError(f"intermediate list index out of range for {path!r}")
            node = node[idx]
        else:
            raise JsonPointerError(f"cannot descend through scalar at {path!r}")
    return node, tokens[-1]
