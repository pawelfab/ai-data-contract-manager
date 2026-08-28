from __future__ import annotations

from typing import Any


def escape_token(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def join_pointer(base: str, token: str) -> str:
    return f"{base}/{escape_token(token)}" if base else f"/{escape_token(token)}"


def resolve_ref(root: dict, schema: dict) -> dict:
    ref = schema.get("$ref")
    if not ref:
        return schema
    if not ref.startswith("#/"):
        raise ValueError(f"baseline supports local $ref only: {ref}")
    node: Any = root
    for token in ref[2:].split("/"):
        node = node[token.replace("~1", "/").replace("~0", "~")]
    merged = dict(node)
    merged.update({k: v for k, v in schema.items() if k != "$ref"})
    return merged


def pointer_get(document: Any, path: str) -> Any:
    if path == "":
        return document
    node = document
    for raw in path[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(node, list):
            node = node[int(token)]
        else:
            node = node[token]
    return node


def pointer_exists(document: Any, path: str) -> bool:
    try:
        pointer_get(document, path)
        return True
    except (KeyError, IndexError, ValueError, TypeError):
        return False
