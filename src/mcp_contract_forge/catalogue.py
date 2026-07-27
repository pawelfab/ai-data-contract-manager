from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Iterable, Mapping, Sequence

from jsonschema.exceptions import SchemaError

from .models import (
    FieldGuidance,
    OptionalDecision,
    RequirementQuestion,
    RequirementsCatalogue,
)
from .schema_utils import JsonObject, fingerprint


class SchemaCatalogue:
    """Build the active, compact contract slice exposed to ACDM."""

    def __init__(
        self,
        schema: JsonObject,
        schema_fingerprint: str,
        *,
        target_order: Sequence[str],
        source_aliases: Mapping[str, str],
    ) -> None:
        self.schema = schema
        self.schema_fingerprint = schema_fingerprint
        self.target_order = tuple(target_order)
        self.source_aliases = dict(source_aliases)

    @property
    def source_types(self) -> list[str]:
        mapping = (
            self.schema["properties"]["source"]["discriminator"]["mapping"]
        )
        return list(mapping)

    def list_contract_options(self) -> JsonObject:
        return {
            "schemaFingerprint": self.schema_fingerprint,
            "sourceTypes": self.source_types,
            "targetLayers": list(self.target_order),
            "targetRules": [
                "Bronze jest obowiązkowa dla każdego źródła raw.",
                "Silver może wystąpić tylko po Bronze.",
                "Gold może wystąpić tylko po Bronze i Silver.",
            ],
        }

    def get_onboarding_requirements(
        self,
        source_type: str,
        target_layers: Iterable[str] | None = None,
    ) -> RequirementsCatalogue:
        source_type = source_type.strip().lower().replace("-", "_")
        source_type = self.source_aliases.get(source_type, source_type)
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
        catalogue_fingerprint = fingerprint(
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
            target_order=list(self.target_order),
            required_paths=required_paths,
            optional_paths=optional_paths,
            allowed_paths=[field.path for field in fields],
            questions=questions,
            optional_decisions=decisions,
            field_catalog=fields,
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
        unknown = [
            layer for layer in layers if layer not in self.target_order
        ]
        if unknown:
            raise ValueError(
                f"Nieznane warstwy target: {', '.join(unknown)}. "
                f"Dozwolone: {', '.join(self.target_order)}."
            )
        if layers[0] != "bronze":
            raise ValueError(
                "Pierwszą i obowiązkową warstwą musi być Bronze."
            )
        expected = list(self.target_order[: len(layers)])
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
