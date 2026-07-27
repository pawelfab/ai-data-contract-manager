from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Iterable, Sequence

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

from .catalogue import SchemaCatalogue
from .models import ValidationIssue, ValidationResult
from .schema_utils import JsonObject, fingerprint


class ContractValidator:
    """Validate contracts and translate JSON Schema errors for the agent."""

    def __init__(
        self,
        schema: JsonObject,
        schema_fingerprint: str,
        catalogue: SchemaCatalogue,
        *,
        target_order: Sequence[str],
    ) -> None:
        Draft202012Validator.check_schema(schema)
        self.validator = Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        )
        self.schema_fingerprint = schema_fingerprint
        self.catalogue = catalogue
        self.target_order = tuple(target_order)

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
            contract_fingerprint=fingerprint(normalized),
            schema_fingerprint=self.schema_fingerprint,
            issues=issues,
            normalized_contract=normalized,
        )

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
            selected_index = self._selected_variant_index(error)
            leaf_errors = [
                nested
                for nested in error.context
                if nested.validator not in {"oneOf", "anyOf"}
                and (
                    selected_index is None
                    or (
                        nested.relative_schema_path
                        and nested.relative_schema_path[0] == selected_index
                    )
                )
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
            for layer in self.target_order
            if isinstance(targets, dict) and layer in targets
        ]
        if source_type in self.catalogue.source_types:
            try:
                active = self.catalogue.get_onboarding_requirements(
                    source_type, layers or ["bronze"]
                )
                by_path = {
                    field.path: field.description
                    for field in active.field_catalog
                }
                if path in by_path:
                    return by_path[path]
                normalized = re.sub(r"\.\d+(?=\.|$)", "", path)
                if normalized in by_path:
                    return by_path[normalized]
                for field in active.field_catalog:
                    prefix = f"{field.path}."
                    if not field.item_properties or not path.startswith(prefix):
                        continue
                    remainder = path[len(prefix) :].split(".")
                    if len(remainder) < 2 or not remainder[0].isdigit():
                        continue
                    item = field.item_properties.get(remainder[1], {})
                    description = item.get("description")
                    if isinstance(description, str) and description:
                        return description
            except ValueError:
                pass
        return "Pole musi być zgodne z aktywnym wariantem kontraktu."

    @staticmethod
    def _selected_variant_index(error: ValidationError) -> int | None:
        schema = error.schema
        instance = error.instance
        if not isinstance(schema, dict) or not isinstance(instance, dict):
            return None
        discriminator = schema.get("discriminator")
        alternatives = schema.get(error.validator)
        if not isinstance(discriminator, dict) or not isinstance(
            alternatives, list
        ):
            return None
        property_name = discriminator.get("propertyName")
        mapping = discriminator.get("mapping")
        if not isinstance(property_name, str) or not isinstance(mapping, dict):
            return None
        selected_ref = mapping.get(instance.get(property_name))
        if not isinstance(selected_ref, str):
            return None
        for index, alternative in enumerate(alternatives):
            if (
                isinstance(alternative, dict)
                and alternative.get("$ref") == selected_ref
            ):
                return index
        return None

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

        ordered_ranges = sorted(ranges, key=lambda item: item[0])
        for previous, current in zip(
            ordered_ranges,
            ordered_ranges[1:],
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
            for layer in self.target_order:
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
        for layer in self.target_order:
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
