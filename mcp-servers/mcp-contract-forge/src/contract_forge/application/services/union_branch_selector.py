from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from contract_forge.utils.pointer import get_pointer

DISCRIMINATOR = "x-discriminator"

_MISSING = object()


class BranchSelectionStatus(StrEnum):
    SELECTED = "selected"
    MISSING_DISCRIMINATOR = "missing_discriminator"
    INVALID_DISCRIMINATOR = "invalid_discriminator"
    AMBIGUOUS = "ambiguous"


class BranchSelection(BaseModel):
    status: BranchSelectionStatus
    branch: dict[str, Any] | None = None
    discriminator_path: str | None = None
    allowed_values: list[Any] = Field(default_factory=list)


class UnionBranchSelector:
    """Picks one `oneOf` branch using the union's declared discriminator.

    Generic on purpose: it knows nothing about any particular contract, model name or value.
    A union without `x-discriminator` is not selectable and stays atomic for the caller.
    """

    def selects(self, schema: dict[str, Any]) -> bool:
        return isinstance(schema.get(DISCRIMINATOR), dict) and bool(schema["oneOf"])

    def select(
        self,
        schema: dict[str, Any],
        path: str,
        document: dict[str, Any],
        defs: dict[str, Any],
    ) -> BranchSelection:
        relative = str(schema[DISCRIMINATOR].get("path") or "")
        selection = self.select_value(schema, get_pointer(document, path, None) if path else document, defs)
        return selection.model_copy(update={"discriminator_path": _join(path, relative)})

    def select_value(
        self,
        schema: dict[str, Any],
        value: Any,
        defs: dict[str, Any],
    ) -> BranchSelection:
        """Same decision, made against the union's own sub-document rather than a pointer."""

        relative = str(schema[DISCRIMINATOR].get("path") or "")
        discriminator_path = "/" + "/".join(_escape(p) for p in _segments(relative))
        options = [(_allowed(branch, relative, defs), branch) for branch in schema["oneOf"]]
        allowed = [item for values, _ in options for item in values]

        value = get_pointer(value, discriminator_path, _MISSING) if isinstance(value, dict) else _MISSING
        if value is _MISSING or value is None:
            return BranchSelection(
                status=BranchSelectionStatus.MISSING_DISCRIMINATOR,
                discriminator_path=discriminator_path,
                allowed_values=allowed,
            )

        matches = [branch for values, branch in options if value in values]
        if len(matches) > 1:
            return BranchSelection(
                status=BranchSelectionStatus.AMBIGUOUS,
                discriminator_path=discriminator_path,
                allowed_values=allowed,
            )
        if not matches:
            return BranchSelection(
                status=BranchSelectionStatus.INVALID_DISCRIMINATOR,
                discriminator_path=discriminator_path,
                allowed_values=allowed,
            )
        return BranchSelection(
            status=BranchSelectionStatus.SELECTED,
            branch=matches[0],
            discriminator_path=discriminator_path,
            allowed_values=allowed,
        )


def discriminator_values(branch: dict[str, Any], relative: str, defs: dict[str, Any]) -> list[Any]:
    """Values of the discriminator a branch accepts, taken from its `const` or `enum`."""

    return _allowed(branch, relative, defs)


def _allowed(branch: Any, relative: str, defs: dict[str, Any]) -> list[Any]:
    node = _resolve(branch, defs)
    for name in _segments(relative):
        node = _resolve(node.get("properties", {}).get(name), defs)
        if not node:
            return []
    if "const" in node:
        return [node["const"]]
    enum = node.get("enum")
    return list(enum) if isinstance(enum, list) else []


def _resolve(schema: Any, defs: dict[str, Any]) -> dict[str, Any]:
    seen: set[str] = set()
    current = schema
    while isinstance(current, dict) and "$ref" in current:
        ref = current["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#/$defs/") or ref in seen:
            return {}
        seen.add(ref)
        current = defs.get(ref.split("/")[-1])
    return current if isinstance(current, dict) else {}


def _segments(relative: str) -> list[str]:
    return [part for part in relative.strip("/").split("/") if part]


def _join(path: str, relative: str) -> str:
    tail = "".join("/" + _escape(part) for part in _segments(relative))
    return f"{path}{tail}"


def _escape(part: str) -> str:
    return part.replace("~", "~0").replace("/", "~1")
