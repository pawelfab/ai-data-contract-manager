from __future__ import annotations

from typing import Any

from contract_forge.application.services.union_branch_selector import (
    BranchSelectionStatus,
    UnionBranchSelector,
)
from contract_forge.utils.pointer import get_pointer


_MISSING = object()
_UNIONS = UnionBranchSelector()


def pointer_exists_in_schema(raw_schema: dict[str, Any], pointer: str) -> bool:
    if pointer == "":
        return True
    if not pointer.startswith("/"):
        return False
    parts = [_unescape(x) for x in pointer[1:].split("/")]
    return _walk(raw_schema, raw_schema.get("$defs", {}), parts)


def enrichment_target_reachable(
    raw_schema: dict[str, Any], document: dict[str, Any], pointer: str
) -> bool:
    """Return whether enrichment may safely materialize a schema path now.

    Visible requirements are handled separately. This helper covers optional enrichment targets:
    a missing leaf under an existing container, or the first leaf that activates one missing
    optional container. It deliberately rejects deeper targets so a rule cannot create an entire
    hidden subtree ahead of discovery.
    """

    if pointer in {"", "/"}:
        return False

    encoded_parts = pointer[1:].split("/")
    parts = [_unescape(x) for x in encoded_parts]
    defs = raw_schema.get("$defs", {})
    if not _reachable_in_active_schema(raw_schema, defs, parts, document, pointer, ""):
        return False

    parent_pointer = "" if len(encoded_parts) == 1 else "/" + "/".join(encoded_parts[:-1])
    parent = document if not parent_pointer else get_pointer(document, parent_pointer, _MISSING)
    if isinstance(parent, (dict, list)):
        return True

    schema = raw_schema
    prefix: list[str] = []
    for index, part in enumerate(parts[:-1]):
        child, optional = _child_schema(schema, defs, part, parts[index + 1 :])
        if child is None:
            return False

        prefix.append(encoded_parts[index])
        current_pointer = "/" + "/".join(prefix)
        current = get_pointer(document, current_pointer, _MISSING)
        if current is _MISSING or current is None:
            is_direct_parent = index == len(parts) - 2
            return optional and is_direct_parent and _objectish(child, defs)
        schema = child

    return False


def _reachable_in_active_schema(
    schema: dict[str, Any],
    defs: dict[str, Any],
    parts: list[str],
    document: dict[str, Any],
    target_pointer: str,
    current_path: str,
) -> bool:
    schema = _resolve(schema, defs)
    if not parts:
        return True

    if "oneOf" in schema:
        if not _UNIONS.selects(schema):
            return False
        selection = _UNIONS.select(schema, current_path, document, defs)
        if selection.status is BranchSelectionStatus.MISSING_DISCRIMINATOR:
            return target_pointer == selection.discriminator_path
        if selection.status is not BranchSelectionStatus.SELECTED or selection.branch is None:
            return False
        return _reachable_in_active_schema(
            selection.branch, defs, parts, document, target_pointer, current_path
        )

    if "anyOf" in schema:
        branches = [b for b in schema["anyOf"] if isinstance(b, dict) and b.get("type") != "null"]
        return any(
            _reachable_in_active_schema(
                branch, defs, parts, document, target_pointer, current_path
            )
            for branch in branches
        )

    head = parts[0]
    next_path = f"{current_path}/{_escape(head)}"
    if schema.get("type") == "array" or "items" in schema:
        if not (head.isdigit() or head in {"*", "[*]"}):
            return False
        items = schema.get("items")
        return isinstance(items, dict) and _reachable_in_active_schema(
            items, defs, parts[1:], document, target_pointer, next_path
        )

    child = schema.get("properties", {}).get(head)
    return isinstance(child, dict) and _reachable_in_active_schema(
        child, defs, parts[1:], document, target_pointer, next_path
    )


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


def _child_schema(
    schema: dict[str, Any], defs: dict[str, Any], part: str, remaining: list[str]
) -> tuple[dict[str, Any] | None, bool]:
    schema = _resolve(schema, defs)
    for key in ("anyOf", "oneOf"):
        if key in schema:
            branches = [b for b in schema[key] if isinstance(b, dict) and b.get("type") != "null"]
            for branch in branches:
                if _walk(branch, defs, [part, *remaining]):
                    return _child_schema(branch, defs, part, remaining)
            return None, False

    if schema.get("type") == "array" or "items" in schema:
        if not (part.isdigit() or part in {"*", "[*]"}):
            return None, False
        items = schema.get("items")
        return (items, False) if isinstance(items, dict) else (None, False)

    props = schema.get("properties", {})
    child = props.get(part)
    if not isinstance(child, dict):
        return None, False
    return child, part not in set(schema.get("required", []))


def _objectish(schema: dict[str, Any], defs: dict[str, Any]) -> bool:
    schema = _resolve(schema, defs)
    if schema.get("type") == "object" or "properties" in schema:
        return True
    for key in ("anyOf", "oneOf"):
        if any(
            _objectish(branch, defs)
            for branch in schema.get(key, [])
            if isinstance(branch, dict) and branch.get("type") != "null"
        ):
            return True
    return False


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


def _escape(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")
