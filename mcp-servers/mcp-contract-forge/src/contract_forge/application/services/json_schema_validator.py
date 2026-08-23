from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator
from pydantic import BaseModel, Field

from contract_forge.application.services.union_branch_selector import (
    BranchSelectionStatus,
    UnionBranchSelector,
)


class SchemaError(BaseModel):
    """One formal JSON Schema violation, normalized away from the library's own types."""

    path: str
    keyword: str
    message: str


class JsonSchemaValidator:
    """The formal authority on whether a document satisfies the contract.

    The Requirement Engine is a discovery tool: it walks the schema the way a conversation
    needs and may legitimately not cover every keyword. Correctness must not depend on that
    walker, so `valid` is decided here, against the complete raw schema.

    This service reports violations and nothing else. Which of them a user should see is a
    presentation decision and lives in `schema_validation_issue_mapper`.
    """

    def __init__(self):
        self.unions = UnionBranchSelector()

    def validate(self, raw_schema: dict[str, Any], document: dict[str, Any]) -> list[SchemaError]:
        defs = raw_schema.get("$defs", {})
        validator = Draft202012Validator(raw_schema)
        errors = sorted(validator.iter_errors(document), key=lambda e: list(e.absolute_path))
        out: list[SchemaError] = []
        for error in errors:
            out.extend(self._expand(error, defs))
        return out

    def _expand(self, error: Any, defs: dict[str, Any]) -> list[SchemaError]:
        """Re-report a failed discriminated union against the branch the document chose.

        A bare `oneOf` failure says only "matches none of the branches", which hides the real
        problem — a wrong value inside the chosen branch would otherwise be invisible. Once the
        discriminator names a branch, that branch is the one to report against.
        """

        prefix = list(error.absolute_path)
        node = error.schema
        if error.validator != "oneOf" or not isinstance(node, dict) or not self.unions.selects(node):
            return [_error(prefix, error.validator, error.message)]

        selection = self.unions.select_value(node, error.instance, defs)
        if selection.status is not BranchSelectionStatus.SELECTED:
            return [_error(prefix, error.validator, error.message)]

        branch = Draft202012Validator({**selection.branch, "$defs": defs})
        nested = sorted(branch.iter_errors(error.instance), key=lambda e: list(e.absolute_path))
        return [
            _error(prefix + list(inner.absolute_path), inner.validator, inner.message)
            for inner in nested
        ] or [_error(prefix, error.validator, error.message)]


def _error(parts: list[Any], keyword: Any, message: str) -> SchemaError:
    return SchemaError(
        path="/" + "/".join(_escape(str(part)) for part in parts),
        keyword=str(keyword),
        message=message,
    )


def _escape(part: str) -> str:
    return part.replace("~", "~0").replace("/", "~1")
