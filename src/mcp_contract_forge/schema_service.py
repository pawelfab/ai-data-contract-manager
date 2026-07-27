from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .catalogue import SchemaCatalogue
from .models import RequirementsCatalogue, ValidationResult, YamlResult
from .schema_utils import JsonObject, fingerprint
from .validation import ContractValidator
from .yaml_renderer import render_contract_yaml


class ContractSchemaService:
    """Facade for catalogue discovery, validation and YAML rendering."""

    TARGET_ORDER = ("bronze", "silver", "gold")
    SOURCE_ALIASES = {
        "fixed_with": "fixed_width",
        "fixedwidth": "fixed_width",
    }

    def __init__(self, schema_path: str | Path | None = None) -> None:
        default_path = (
            Path(__file__).resolve().parents[2]
            / "contracts"
            / "data-contract.schema.json"
        )
        self.schema_path = Path(schema_path) if schema_path else default_path
        self.schema: JsonObject = json.loads(
            self.schema_path.read_text(encoding="utf-8")
        )
        self.schema_fingerprint = fingerprint(self.schema)
        self.catalogue = SchemaCatalogue(
            self.schema,
            self.schema_fingerprint,
            target_order=self.TARGET_ORDER,
            source_aliases=self.SOURCE_ALIASES,
        )
        self.validation = ContractValidator(
            self.schema,
            self.schema_fingerprint,
            self.catalogue,
            target_order=self.TARGET_ORDER,
        )
        # Kept for compatibility with callers that inspect the jsonschema
        # validator exposed by the original service.
        self.validator = self.validation.validator

    @property
    def source_types(self) -> list[str]:
        return self.catalogue.source_types

    def list_contract_options(self) -> JsonObject:
        return self.catalogue.list_contract_options()

    def get_onboarding_requirements(
        self,
        source_type: str,
        target_layers: Iterable[str] | None = None,
    ) -> RequirementsCatalogue:
        return self.catalogue.get_onboarding_requirements(
            source_type,
            target_layers,
        )

    def validate_contract(self, contract: JsonObject) -> ValidationResult:
        return self.validation.validate_contract(contract)

    def generate_contract_yaml(self, contract: JsonObject) -> YamlResult:
        return render_contract_yaml(self.validate_contract(contract))
