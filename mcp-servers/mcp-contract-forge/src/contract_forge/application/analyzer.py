import re
from typing import Any

from jsonschema import Draft202012Validator

from contract_forge.domain.definition import ContractDefinition
from contract_forge.domain.protocol import (
    PROTOCOL_VERSION,
    ContractStatus,
    Diagnostic,
    ForeignLocation,
    ForgeAnalysis,
    ForgeProposal,
    MissingRequirement,
    WritableTarget,
)
from contract_forge.ports.definition_repository import ContractDefinitionPort

from .schema_utils import join_pointer, pointer_exists, pointer_get, resolve_ref

_TEMPLATE = re.compile(r"\{(/[^{}]+)\}")


class ContractAnalyzer:
    def __init__(self, definitions: ContractDefinitionPort) -> None:
        self.definitions = definitions

    def analyze(self, document: dict) -> ForgeAnalysis:
        definition = self.definitions.load()
        schema = definition.schema_document
        missing = self._missing(schema, schema, document, "")
        foreign = self._foreign(schema, schema, document, "")
        diagnostics = self._diagnostics(schema, document)
        proposals = self._default_proposals(schema, schema, document, "")
        proposals.extend(self._enrichment_proposals(definition, document))
        writable = self._writable(schema, schema, "", required=True)
        status = ContractStatus(
            valid=not any(item.severity == "error" for item in diagnostics),
            complete=not missing,
            clean=not foreign,
        )
        return ForgeAnalysis(
            protocol_version=PROTOCOL_VERSION,
            definition_version=definition.version,
            writable=writable,
            missing=missing,
            foreign=foreign,
            proposals=proposals,
            diagnostics=diagnostics,
            status=status,
        )

    def _missing(self, root: dict, schema: dict, value: Any, path: str) -> list[MissingRequirement]:
        schema = resolve_ref(root, schema)
        if schema.get("type") != "object" or not isinstance(value, dict):
            return []
        result: list[MissingRequirement] = []
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))
        for name in required:
            child_path = join_pointer(path, name)
            child_schema = resolve_ref(root, properties.get(name, {}))
            if name not in value:
                result.extend(self._missing_for_absent_required(root, child_schema, child_path))
        for name, child_value in value.items():
            if name in properties:
                result.extend(self._missing(root, properties[name], child_value, join_pointer(path, name)))
        return result


    def _missing_for_absent_required(self, root: dict, schema: dict, path: str) -> list[MissingRequirement]:
        schema = resolve_ref(root, schema)
        if schema.get("type") == "object" and schema.get("required"):
            properties = schema.get("properties", {})
            result: list[MissingRequirement] = []
            for name in schema.get("required", []):
                child_path = join_pointer(path, name)
                child_schema = resolve_ref(root, properties.get(name, {}))
                result.extend(self._missing_for_absent_required(root, child_schema, child_path))
            return result
        return [
            MissingRequirement(
                path=path,
                message=f"Required value missing at {path}",
                expected_type=schema.get("type"),
                allowed_values=schema.get("enum"),
            )
        ]

    def _foreign(self, root: dict, schema: dict, value: Any, path: str) -> list[ForeignLocation]:
        schema = resolve_ref(root, schema)
        result: list[ForeignLocation] = []
        if schema.get("type") == "object" and isinstance(value, dict):
            properties = schema.get("properties", {})
            admissible = sorted(properties)
            for name, child in value.items():
                child_path = join_pointer(path, name)
                if name not in properties:
                    result.append(
                        ForeignLocation(
                            path=child_path,
                            reason="field is not part of the active schema shape",
                            admissible_fields=admissible,
                        )
                    )
                else:
                    result.extend(self._foreign(root, properties[name], child, child_path))
        elif schema.get("type") == "array" and isinstance(value, list):
            item_schema = schema.get("items", {})
            for idx, item in enumerate(value):
                result.extend(self._foreign(root, item_schema, item, join_pointer(path, str(idx))))
        return result

    @staticmethod
    def _diagnostics(schema: dict, document: dict) -> list[Diagnostic]:
        result: list[Diagnostic] = []
        for error in Draft202012Validator(schema).iter_errors(document):
            if error.validator in {"required", "additionalProperties"}:
                continue
            path = "".join(f"/{str(part).replace('~', '~0').replace('/', '~1')}" for part in error.absolute_path)
            result.append(
                Diagnostic(
                    code=str(error.validator),
                    path=path or None,
                    message=error.message,
                    actual_value=error.instance,
                )
            )
        return result

    def _writable(self, root: dict, schema: dict, path: str, required: bool) -> list[WritableTarget]:
        schema = resolve_ref(root, schema)
        result: list[WritableTarget] = []
        schema_type = schema.get("type")
        if path:
            result.append(
                WritableTarget(
                    path=path,
                    value_type=schema_type,
                    allowed_values=schema.get("enum"),
                    title=schema.get("title"),
                    description=schema.get("description"),
                    activatable=not required and schema_type in {"object", "array"},
                )
            )
        if schema_type == "object":
            required_names = set(schema.get("required", []))
            for name, child in schema.get("properties", {}).items():
                result.extend(self._writable(root, child, join_pointer(path, name), name in required_names))
        elif schema_type == "array":
            result.extend(self._writable(root, schema.get("items", {}), join_pointer(path, "*"), required=False))
        return result

    def _default_proposals(self, root: dict, schema: dict, document: Any, path: str) -> list[ForgeProposal]:
        schema = resolve_ref(root, schema)
        result: list[ForgeProposal] = []
        if path and "default" in schema:
            result.append(
                ForgeProposal(
                    id=f"default:{path}",
                    rule_id=f"default:{path}",
                    path=path,
                    value=schema["default"],
                    origin="default",
                    reason="JSON Schema default",
                )
            )
        if schema.get("type") == "object" and isinstance(document, dict):
            for name, child_schema in schema.get("properties", {}).items():
                if name in document:
                    result.extend(self._default_proposals(root, child_schema, document[name], join_pointer(path, name)))
                elif "default" in resolve_ref(root, child_schema):
                    result.extend(self._default_proposals(root, child_schema, None, join_pointer(path, name)))
        elif schema.get("type") == "array" and isinstance(document, list):
            for idx, item in enumerate(document):
                result.extend(self._default_proposals(root, schema.get("items", {}), item, join_pointer(path, str(idx))))
        return result

    def _enrichment_proposals(self, definition: ContractDefinition, document: dict) -> list[ForgeProposal]:
        result: list[ForgeProposal] = []
        for raw in definition.enrichments:
            if not self._when_matches(raw.get("when"), document):
                continue
            try:
                value, deps = self._render(raw.get("value"), document)
            except KeyError:
                continue
            rule_id = str(raw.get("id") or f"enrichment:{raw.get('path')}")
            result.append(
                ForgeProposal(
                    id=rule_id,
                    rule_id=rule_id,
                    path=raw["path"],
                    value=value,
                    origin="enrichment",
                    reason=str(raw.get("reason") or rule_id),
                    derived_from=deps,
                )
            )
        return result

    def _when_matches(self, raw_when: Any, document: dict) -> bool:
        if raw_when is None:
            return True
        conditions = raw_when if isinstance(raw_when, list) else [raw_when]
        for condition in conditions:
            path = condition["path"]
            present = pointer_exists(document, path)
            if "exists" in condition and present != bool(condition["exists"]):
                return False
            if "equals" in condition and (not present or pointer_get(document, path) != condition["equals"]):
                return False
        return True

    def _render(self, value: Any, document: dict) -> tuple[Any, list[str]]:
        if not isinstance(value, str):
            return value, []
        deps: list[str] = []
        exact = _TEMPLATE.fullmatch(value)
        if exact:
            path = exact.group(1)
            return pointer_get(document, path), [path]

        def replace(match: re.Match[str]) -> str:
            path = match.group(1)
            deps.append(path)
            return str(pointer_get(document, path))

        return _TEMPLATE.sub(replace, value), deps
