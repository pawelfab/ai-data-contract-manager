from __future__ import annotations

from typing import Any


def pointer_exists_in_schema(raw_schema: dict[str, Any], pointer: str) -> bool:
    if pointer == "":
        return True
    if not pointer.startswith("/"):
        return False
    parts = [_unescape(x) for x in pointer[1:].split("/")]
    return _walk(raw_schema, raw_schema.get("$defs", {}), parts)


def _walk(schema: dict[str, Any], defs: dict[str, Any], parts: list[str]) -> bool:
    schema = _resolve(schema, defs)
    if not parts:
        return True

    # anyOf/oneOf is a union: a path is valid if any non-null branch contains it.
    for key in ("anyOf", "oneOf"):
        if key in schema:
            branches = [b for b in schema[key] if isinstance(b, dict) and b.get("type") != "null"]
            return any(_walk(branch, defs, parts) for branch in branches)

    if schema.get("type") == "array" or "items" in schema:
        head = parts[0]
        if not (head.isdigit() or head in {"*", "[*]"}):
            return False
        items = schema.get("items")
        return isinstance(items, dict) and _walk(items, defs, parts[1:])

    props = schema.get("properties", {})
    head = parts[0]
    child = props.get(head)
    if not isinstance(child, dict):
        return False
    return _walk(child, defs, parts[1:])


def _resolve(schema: dict[str, Any], defs: dict[str, Any]) -> dict[str, Any]:
    seen: set[str] = set()
    current = schema
    while isinstance(current, dict) and "$ref" in current:
        ref = current["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#/$defs/") or ref in seen:
            break
        seen.add(ref)
        current = defs.get(ref.split("/")[-1], {})
    return current


def _unescape(value: str) -> str:
    return value.replace("~1", "/").replace("~0", "~")
