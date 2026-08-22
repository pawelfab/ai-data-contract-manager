from typing import Any

from contract_forge.domain.contract.models import NormalizedContract

from .rule_parser import parse_rules
from .schema_parser import parse_schema
from .source_linter import lint_source
from .semantic_paths import SEMANTIC_PATHS_V1


class ContractJsonV1Parser:
    """The only adapter that understands the current contract.json v1 layout."""

    def parse(self, raw: dict[str, Any]) -> NormalizedContract:
        problems = lint_source(raw)
        if problems:
            details = "; ".join(f"{p.location}: {p.message}" for p in problems)
            raise ValueError(f"Invalid contract source: {details}")

        return NormalizedContract(
            root=parse_schema(raw),
            rules=parse_rules(raw),
            raw_schema=raw,
            defs=raw.get("$defs", {}),
            rules_spec_version=raw.get("x-contract-rules-spec", {}).get("version"),
            semantic_paths=SEMANTIC_PATHS_V1,
        )
