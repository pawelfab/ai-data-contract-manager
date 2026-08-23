from __future__ import annotations

from contract_forge.application.services.json_schema_validator import SchemaError
from contract_forge.domain.evaluation.models import ValidationIssue

# Keywords whose violation means "something is still missing" or "this union did not match".
# Neither is a useful message while the contract is being built: absence is what
# `requirements` are for, and a union container error cannot tell a wrong discriminator apart
# from a right discriminator with an unfinished branch. Precise messages for those come from
# UnionBranchSelector, the schema engine and the rule engine.
STRUCTURAL_KEYWORDS = frozenset({"required", "oneOf", "anyOf", "allOf"})


def map_schema_errors(errors: list[SchemaError]) -> list[ValidationIssue]:
    """Decide which formal violations a user should see.

    Presentation policy lives here rather than in the validator, so changing what is surfaced
    never changes what `valid` is computed from.
    """

    return [
        ValidationIssue(path=error.path or None, severity="error", message=error.message)
        for error in errors
        if error.keyword not in STRUCTURAL_KEYWORDS
    ]
