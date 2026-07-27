from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError, ValidationError

from .models import (
    FieldGuidance,
    OptionalDecision,
    RequirementQuestion,
    RequirementsCatalogue,
    ValidationIssue,
    ValidationResult,
    YamlResult,
)

JsonObject = dict[str, Any]


class ContractSchemaService:
    """Read one JSON Schema and expose only the active contract slice."""

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
        Draft202012Validator.check_schema(self.schema)
        self.validator = Draft202012Validator(
            self.schema,
            format_checker=FormatChecker(),
        )
        self.schema_fingerprint = self._fingerprint(self.schema)

    def list_contract_options(self) -> JsonObject:
        return {
            "schemaFingerprint": self.schema_fingerprint,
            "sourceTypes": self.source_types,
            "targetLayers": list(self.TARGET_ORDER),
            "targetRules": [
                "Bronze jest obowiązkowa dla każdego źródła raw.",
                "Silver może wystąpić tylko po Bronze.",
                "Gold może wystąpić tylko po Bronze i Silver.",
            ],
        }

    @property
    def source_types(self) -> list[str]:
        mapping = (
            self.schema["properties"]["source"]["discriminator"]["mapping"]
        )
        return list(mapping)

    def get_onboarding_requirements(
        self,
        source_type: str,
        target_layers: Iterable[str] | None = None,
    ) -> RequirementsCatalogue:
        source_type = source_type.strip().lower().replace("-", "_")
        source_type = self.SOURCE_ALIASES.get(source_type, source_type)
        if source_type not in self.source_types:
            allowed = ", ".join(self.source_types)
            raise ValueError(
                f"Nieznany source_type={source_type!r}. Dozwolone: {allowed}."
            )

        layers = self._normalize_target_layers(target_layers)
        fields: list[FieldGuidance] = []
        decisions: list[OptionalDecision] = []

        self._collect_fields(
            self.schema["properties"]["metadata"],
            "metadata",
            parent_required=True,
            fields=fields,
            decisions=decisions,
        )

        source_ref = self.schema["properties"]["source"]["discriminator"][
            "mapping"
        ][source_type]
        self._collect_fields(
            {"$ref": source_ref},
            "source",
            parent_required=True,
            fields=fields,
            decisions=decisions,
        )

        target_properties = self._resolve(
            self.schema["properties"]["targets"]
        )["properties"]
        for layer in layers:
            self._collect_fields(
                target_properties[layer],
                f"targets.{layer}",
                parent_required=True,
                fields=fields,
                decisions=decisions,
            )

        self._collect_fields(
            self.schema["properties"]["orchestration"],
            "orchestration",
            parent_required=True,
            fields=fields,
            decisions=decisions,
        )

        required_paths = [field.path for field in fields if field.required]
        optional_paths = [field.path for field in fields if not field.required]
        questions = [
            RequirementQuestion(
                path=field.path,
                question=self._question_for(field),
                description=field.description,
                examples=field.examples,
            )
            for field in fields
            if field.required and field.const is None
        ]
        catalogue_fingerprint = self._fingerprint(
            {
                "schema": self.schema_fingerprint,
                "sourceType": source_type,
                "targetLayers": layers,
            }
        )
        return RequirementsCatalogue(
            schema_fingerprint=self.schema_fingerprint,
            fingerprint=catalogue_fingerprint,
            source_type=source_type,
            target_layers=layers,
            source_types=self.source_types,
            target_order=list(self.TARGET_ORDER),
            required_paths=required_paths,
            optional_paths=optional_paths,
            allowed_paths=[field.path for field in fields],
            questions=questions,
            optional_decisions=decisions,
            field_catalog=fields,
        )

    def validate_contract(self, contract: JsonObject) -> ValidationResult:
        normalized = deepcopy(contract)
        issues: list[ValidationIssue] = []

        for error in sorted(
            self.validator.iter_errors(normalized),
            key=lambda item: (list(item.absolute_path), item.message),
        ):
            issues.extend(self._issues_from_error(error, normalized))

        issues.extend(self._validate_fixed_width(normalized))
        issues.extend(self._validate_unique_column_names(normalized))
        issues.extend(self._validate_target_source_paths(normalized))
        issues = self._deduplicate_issues(issues)

        return ValidationResult(
            valid=not issues,
            contract_fingerprint=self._fingerprint(normalized),
            schema_fingerprint=self.schema_fingerprint,
            issues=issues,
            normalized_contract=normalized,
        )

    def generate_contract_yaml(self, contract: JsonObject) -> YamlResult:
        result = self.validate_contract(contract)
        if not result.valid:
            summary = "; ".join(
                f"{issue.path or '<root>'}: {issue.message}"
                for issue in result.issues[:5]
            )
            raise ValueError(
                "Kontrakt nie przeszedł walidacji i nie może zostać "
                f"wyrenderowany: {summary}"
            )

        rendered = yaml.safe_dump(
            result.normalized_contract,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )
        return YamlResult(
            yaml=rendered,
            contract_fingerprint=result.contract_fingerprint,
            schema_fingerprint=self.schema_fingerprint,
        )

    def _normalize_target_layers(
        self, target_layers: Iterable[str] | None
    ) -> list[str]:
        raw_layers = list(target_layers or ["bronze"])
        layers = [str(layer).strip().lower() for layer in raw_layers]
        if not layers:
            layers = ["bronze"]
        if len(layers) != len(set(layers)):
            raise ValueError("Lista target_layers zawiera duplikaty.")
        unknown = [layer for layer in layers if layer not in self.TARGET_ORDER]
        if unknown:
            raise ValueError(
                f"Nieznane warstwy target: {', '.join(unknown)}. "
                f"Dozwolone: {', '.join(self.TARGET_ORDER)}."
            )
        if layers[0] != "bronze":
            raise ValueError("Pierwszą i obowiązkową warstwą musi być Bronze.")
        expected = list(self.TARGET_ORDER[: len(layers)])
        if layers != expected:
            raise ValueError(
                "Warstwy muszą tworzyć ciąg: bronze, opcjonalnie silver, "
                "opcjonalnie gold."
            )
        return layers

    def _resolve(self, node: JsonObject) -> JsonObject:
        if "$ref" not in node:
            return deepcopy(node)
        ref = node["$ref"]
        if not ref.startswith("#/"):
            raise SchemaError(f"Zewnętrzne $ref nie jest obsługiwane: {ref}")
        resolved: Any = self.schema
        for segment in ref[2:].split("/"):
            segment = segment.replace("~1", "/").replace("~0", "~")
            resolved = resolved[segment]
        merged = deepcopy(resolved)
        for key, value in node.items():
            if key != "$ref":
                merged[key] = deepcopy(value)
        return merged

    def _collect_fields(
        self,
        node: JsonObject,
        path: str,
        *,
        parent_required: bool,
        fields: list[FieldGuidance],
        decisions: list[OptionalDecision],
        condition: str | None = None,
        required_if_path: str | None = None,
    ) -> None:
        resolved = self._resolve(node)
        optional = resolved.get("x-acdm-optional-decision")
        if optional:
            decisions.append(
                OptionalDecision(
                    path=path,
                    label=optional["label"],
                    question=optional["question"],
                    description=resolved.get("description", ""),
                    examples=list(resolved.get("examples", [])),
                )
            )
            condition = f"wymagane po wybraniu opcjonalnej sekcji {path}"
            required_if_path = path

        properties = resolved.get("properties")
        kind = self._kind(resolved)
        if properties and kind == "object":
            required_names = set(resolved.get("required", []))
            for name, child in properties.items():
                locally_required = name in required_names
                child_required = parent_required and locally_required
                child_path = f"{path}.{name}"
                child_resolved = self._resolve(child)
                child_is_object = (
                    self._kind(child_resolved) == "object"
                    and bool(child_resolved.get("properties"))
                )
                if child_required:
                    child_required_if_path = None
                elif locally_required:
                    child_required_if_path = required_if_path
                elif child_is_object:
                    child_required_if_path = child_path
                else:
                    child_required_if_path = None
                self._collect_fields(
                    child,
                    child_path,
                    parent_required=child_required,
                    fields=fields,
                    decisions=decisions,
                    condition=(
                        f"wymagane, gdy istnieje sekcja {child_required_if_path}"
                        if child_required_if_path
                        else None
                    ),
                    required_if_path=child_required_if_path,
                )
            return

        item_required: list[str] = []
        item_properties: dict[str, dict[str, Any]] = {}
        if kind == "array" and isinstance(resolved.get("items"), dict):
            item_schema = self._resolve(resolved["items"])
            item_required = list(item_schema.get("required", []))
            for name, item_node in item_schema.get("properties", {}).items():
                item_resolved = self._resolve(item_node)
                item_properties[name] = self._compact_schema(item_resolved)

        fields.append(
            FieldGuidance(
                path=path,
                kind=kind,
                required=parent_required,
                description=resolved.get("description", ""),
                examples=list(resolved.get("examples", [])),
                default=resolved.get("default"),
                enum=list(resolved.get("enum", [])),
                const=resolved.get("const"),
                item_required=item_required,
                item_properties=item_properties,
                condition=condition,
                required_if_path=required_if_path,
            )
        )

    def _compact_schema(self, node: JsonObject) -> JsonObject:
        keys = (
            "type",
            "description",
            "examples",
            "default",
            "enum",
            "const",
            "minimum",
            "maximum",
            "minLength",
            "maxLength",
            "pattern",
        )
        result = {key: deepcopy(node[key]) for key in keys if key in node}
        if "$ref" in node:
            return self._compact_schema(self._resolve(node))
        return result

    @staticmethod
    def _kind(node: JsonObject) -> str:
        if "type" in node:
            value = node["type"]
            return value if isinstance(value, str) else " | ".join(value)
        if "const" in node:
            return type(node["const"]).__name__
        if "oneOf" in node:
            return "oneOf"
        if "anyOf" in node:
            return "anyOf"
        return "unknown"

    @staticmethod
    def _question_for(field: FieldGuidance) -> str:
        if field.examples:
            return (
                f"Podaj wartość dla `{field.path}`. "
                f"Przykład: {json.dumps(field.examples[0], ensure_ascii=False)}"
            )
        return f"Podaj wartość dla `{field.path}`."

    def _issues_from_error(
        self, error: ValidationError, contract: JsonObject
    ) -> list[ValidationIssue]:
        path = self._path(error.absolute_path)
        if error.validator == "required":
            instance = error.instance if isinstance(error.instance, dict) else {}
            missing = [
                name
                for name in error.validator_value
                if name not in instance
            ]
            return [
                self._issue(
                    f"{path}.{name}" if path else str(name),
                    "required",
                    f"Brakuje wymaganego pola `{name}`.",
                    None,
                    contract,
                )
                for name in missing
            ]

        if error.validator == "dependentRequired":
            instance = error.instance if isinstance(error.instance, dict) else {}
            missing_dependencies = [
                dependency
                for trigger, dependencies in error.validator_value.items()
                if trigger in instance
                for dependency in dependencies
                if dependency not in instance
            ]
            return [
                self._issue(
                    f"{path}.{name}" if path else str(name),
                    "required",
                    f"Brakuje wymaganej wcześniejszej warstwy `{name}`.",
                    None,
                    contract,
                )
                for name in missing_dependencies
            ]

        if error.validator in {"oneOf", "anyOf"} and error.context:
            leaf_errors = [
                nested
                for nested in error.context
                if nested.validator not in {"oneOf", "anyOf"}
            ]
            if leaf_errors:
                return [
                    issue
                    for nested in leaf_errors
                    for issue in self._issues_from_error(nested, contract)
                ]

        return [
            self._issue(
                path,
                str(error.validator),
                error.message,
                error.instance,
                contract,
            )
        ]

    def _issue(
        self,
        path: str,
        code: str,
        message: str,
        value: Any,
        contract: JsonObject,
    ) -> ValidationIssue:
        return ValidationIssue(
            path=path,
            code=code,
            message=message,
            description=self._description_for_path(path, contract),
            value=value,
        )

    def _description_for_path(
        self, path: str, contract: JsonObject
    ) -> str:
        source_type = (
            contract.get("source", {}).get("sourceType")
            if isinstance(contract.get("source"), dict)
            else None
        )
        targets = contract.get("targets", {})
        layers = [
            layer
            for layer in self.TARGET_ORDER
            if isinstance(targets, dict) and layer in targets
        ]
        if source_type in self.source_types:
            try:
                catalogue = self.get_onboarding_requirements(
                    source_type, layers or ["bronze"]
                )
                by_path = {
                    field.path: field.description
                    for field in catalogue.field_catalog
                }
                if path in by_path:
                    return by_path[path]
                normalized = re.sub(r"\.\d+(?=\.|$)", "", path)
                if normalized in by_path:
                    return by_path[normalized]
            except ValueError:
                pass
        return "Pole musi być zgodne z aktywnym wariantem kontraktu."

    def _validate_fixed_width(
        self, contract: JsonObject
    ) -> list[ValidationIssue]:
        source = contract.get("source")
        if not isinstance(source, dict):
            return []
        if source.get("sourceType") != "fixed_width":
            return []
        columns = source.get("columns")
        if not isinstance(columns, list):
            return []

        issues: list[ValidationIssue] = []
        ranges: list[tuple[int, int, int]] = []
        for index, column in enumerate(columns):
            if not isinstance(column, dict):
                continue
            start = column.get("start")
            end = column.get("end")
            if isinstance(start, int) and isinstance(end, int):
                if end <= start:
                    issues.append(
                        ValidationIssue(
                            path=f"source.columns.{index}.end",
                            code="fixed_width.invalid_range",
                            message="`end` musi być większe od `start`.",
                            description=(
                                "Zakres fixed-width jest półotwarty [start, end)."
                            ),
                            value=end,
                        )
                    )
                else:
                    ranges.append((start, end, index))

        for previous, current in zip(
            sorted(ranges, key=lambda item: item[0]),
            sorted(ranges, key=lambda item: item[0])[1:],
        ):
            if current[0] < previous[1]:
                issues.append(
                    ValidationIssue(
                        path=f"source.columns.{current[2]}.start",
                        code="fixed_width.overlap",
                        message=(
                            "Zakres kolumny nakłada się na poprzednią kolumnę."
                        ),
                        description=(
                            "Zakresy kolumn fixed-width nie mogą się nakładać."
                        ),
                        value=current[0],
                    )
                )

        record_length = (
            source.get("options", {}).get("recordLength")
            if isinstance(source.get("options"), dict)
            else None
        )
        if isinstance(record_length, int) and ranges:
            max_end = max(end for _, end, _ in ranges)
            if record_length < max_end:
                issues.append(
                    ValidationIssue(
                        path="source.options.recordLength",
                        code="fixed_width.record_too_short",
                        message=(
                            "recordLength nie może być mniejsze od największego "
                            "końca kolumny."
                        ),
                        description="Oczekiwana liczba znaków w rekordzie.",
                        value=record_length,
                    )
                )
        return issues

    def _validate_unique_column_names(
        self, contract: JsonObject
    ) -> list[ValidationIssue]:
        paths: list[tuple[str, Any]] = []
        source = contract.get("source")
        if isinstance(source, dict):
            if isinstance(source.get("columns"), list):
                paths.append(("source.columns", source["columns"]))
            elif isinstance(source.get("column"), dict):
                paths.append(("source.column", [source["column"]]))
        targets = contract.get("targets")
        if isinstance(targets, dict):
            for layer in self.TARGET_ORDER:
                target = targets.get(layer)
                if isinstance(target, dict) and isinstance(
                    target.get("columns"), list
                ):
                    paths.append((f"targets.{layer}.columns", target["columns"]))

        issues: list[ValidationIssue] = []
        for path, columns in paths:
            names: set[str] = set()
            for index, column in enumerate(columns):
                name = column.get("name") if isinstance(column, dict) else None
                if isinstance(name, str) and name in names:
                    issues.append(
                        ValidationIssue(
                            path=f"{path}.{index}.name",
                            code="columns.duplicate_name",
                            message=f"Powtórzona nazwa kolumny `{name}`.",
                            description=(
                                "Nazwy kolumn w jednej sekcji muszą być unikalne."
                            ),
                            value=name,
                        )
                    )
                elif isinstance(name, str):
                    names.add(name)
        return issues

    def _validate_target_source_paths(
        self, contract: JsonObject
    ) -> list[ValidationIssue]:
        source = contract.get("source")
        available: dict[str, set[str]] = {}
        if isinstance(source, dict):
            source_columns = source.get("columns")
            if not isinstance(source_columns, list) and isinstance(
                source.get("column"), dict
            ):
                source_columns = [source["column"]]
            if isinstance(source_columns, list):
                available["source"] = {
                    column["name"]
                    for column in source_columns
                    if isinstance(column, dict)
                    and isinstance(column.get("name"), str)
                }

        issues: list[ValidationIssue] = []
        targets = contract.get("targets")
        if not isinstance(targets, dict):
            return issues
        previous_scope = "source"
        for layer in self.TARGET_ORDER:
            target = targets.get(layer)
            if not isinstance(target, dict):
                continue
            columns = target.get("columns")
            if not isinstance(columns, list):
                continue
            previous_names = available.get(previous_scope, set())
            for index, column in enumerate(columns):
                if not isinstance(column, dict):
                    continue
                source_path = column.get("sourcePath")
                if not isinstance(source_path, str):
                    continue
                source_name = source_path.rsplit(".", maxsplit=1)[-1]
                if source_name not in previous_names:
                    issues.append(
                        ValidationIssue(
                            path=(
                                f"targets.{layer}.columns.{index}.sourcePath"
                            ),
                            code="target.unknown_source_column",
                            message=(
                                f"Ścieżka wskazuje nieznaną kolumnę "
                                f"`{source_name}` poprzedniej warstwy."
                            ),
                            description=(
                                "sourcePath musi wskazywać kolumnę source dla "
                                "Bronze albo kolumnę bezpośrednio poprzedniej "
                                "warstwy dla Silver/Gold."
                            ),
                            value=source_path,
                        )
                    )
            available[f"targets.{layer}"] = {
                column["name"]
                for column in columns
                if isinstance(column, dict)
                and isinstance(column.get("name"), str)
            }
            previous_scope = f"targets.{layer}"
        return issues

    @staticmethod
    def _deduplicate_issues(
        issues: list[ValidationIssue],
    ) -> list[ValidationIssue]:
        result: list[ValidationIssue] = []
        seen: set[tuple[str, str, str]] = set()
        for issue in issues:
            key = (issue.path, issue.code, issue.message)
            if key not in seen:
                seen.add(key)
                result.append(issue)
        return result

    @staticmethod
    def _path(parts: Iterable[Any]) -> str:
        return ".".join(str(part) for part in parts)

    @staticmethod
    def _fingerprint(value: Any) -> str:
        canonical = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()
