from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

from jsonschema import Draft202012Validator

from .models import Origin, Requirement, ValidationIssue
from .path_utils import get_path, has_path, set_path


class SchemaNavigator:
    """Small dynamic JSON Schema navigator for the contract subset used by ADCM.

    It intentionally delegates final correctness to jsonschema. It resolves local $refs,
    selects the active source discriminator branch, discovers required leaf values, and
    injects JSON Schema defaults without hard-coding contract field names except for the
    discriminator lookup itself.
    """

    def __init__(self, schema: dict[str, Any]):
        self.schema = schema
        self.validator = Draft202012Validator(schema)

    def resolve_ref(self, node: dict[str, Any]) -> dict[str, Any]:
        if "$ref" not in node:
            return node
        ref = node["$ref"]
        if not ref.startswith("#/"):
            raise ValueError(f"Only local refs are supported in the minimal build: {ref}")
        target: Any = self.schema
        for part in ref[2:].split("/"):
            target = target[part.replace("~1", "/").replace("~0", "~")]
        merged = deepcopy(target)
        for k, v in node.items():
            if k != "$ref":
                merged[k] = deepcopy(v)
        return merged

    def active_node(self, node: dict[str, Any], value: Any = None) -> dict[str, Any]:
        node = self.resolve_ref(node)
        if "oneOf" in node and isinstance(value, dict):
            discriminator = node.get("discriminator", {}).get("propertyName")
            if discriminator and discriminator in value:
                wanted = value[discriminator]
                mapping = node.get("discriminator", {}).get("mapping", {})
                mapped_ref = mapping.get(wanted)
                if mapped_ref:
                    return self.resolve_ref({"$ref": mapped_ref})
                for branch in node["oneOf"]:
                    resolved = self.resolve_ref(branch)
                    prop = resolved.get("properties", {}).get(discriminator, {})
                    if prop.get("const") == wanted:
                        return resolved
        return node

    def schema_at_path(self, path: str, contract: dict[str, Any]) -> dict[str, Any] | None:
        parts = [p for p in path.split(".") if p]
        node = self.schema
        current_value: Any = contract
        for i, part in enumerate(parts):
            node = self.active_node(node, current_value)
            node = self.resolve_ref(node)
            if node.get("type") == "array":
                node = self.resolve_ref(node.get("items", {}))
                if part.isdigit():
                    current_value = current_value[int(part)] if isinstance(current_value, list) and int(part) < len(current_value) else None
                    continue
            props = node.get("properties", {})
            if part not in props:
                return None
            node = props[part]
            current_value = current_value.get(part) if isinstance(current_value, dict) else None
        return self.active_node(node, current_value)

    def path_exists_in_schema(self, path: str, contract: dict[str, Any]) -> bool:
        return self.schema_at_path(path, contract) is not None

    def source_type_values(self) -> list[str]:
        """Return source discriminator values without depending on a concrete branch."""
        source = self.resolve_ref(self.schema.get("properties", {}).get("source", {}))
        mapping = source.get("discriminator", {}).get("mapping", {})
        if mapping:
            return list(mapping.keys())
        values: list[str] = []
        discriminator = source.get("discriminator", {}).get("propertyName", "sourceType")
        for branch in source.get("oneOf", []):
            resolved = self.resolve_ref(branch)
            const = resolved.get("properties", {}).get(discriminator, {}).get("const")
            if isinstance(const, str):
                values.append(const)
        return values

    def inject_defaults(self, contract: dict[str, Any], origins: dict[str, Origin]) -> list[tuple[str, Any]]:
        applied: list[tuple[str, Any]] = []

        def walk(node: dict[str, Any], value: Any, path: str, active: bool = True) -> None:
            node = self.active_node(node, value)
            node = self.resolve_ref(node)
            typ = node.get("type")
            if isinstance(value, dict):
                for name, child in node.get("properties", {}).items():
                    child = self.resolve_ref(child)
                    child_path = f"{path}.{name}" if path else name
                    if name not in value and "default" in child:
                        value[name] = deepcopy(child["default"])
                        origins[child_path] = Origin.SCHEMA_DEFAULT
                        applied.append((child_path, deepcopy(child["default"])))
                    if name in value:
                        walk(child, value[name], child_path)
            elif isinstance(value, list):
                item_schema = node.get("items", {})
                for idx, item in enumerate(value):
                    walk(item_schema, item, f"{path}.{idx}")

        walk(self.schema, contract, "")
        return applied

    def ensure_required_containers(self, contract: dict[str, Any], origins: dict[str, Origin]) -> None:
        def walk(node: dict[str, Any], value: Any, path: str) -> None:
            node = self.active_node(node, value)
            node = self.resolve_ref(node)
            if not isinstance(value, dict):
                return
            required = set(node.get("required", []))
            props = node.get("properties", {})
            for name in required:
                child = self.resolve_ref(props.get(name, {}))
                child_path = f"{path}.{name}" if path else name
                if name not in value and child.get("type") == "object":
                    value[name] = {}
                    origins[child_path] = Origin.STRUCTURAL
                if name in value:
                    walk(child, value[name], child_path)
            for name, child in props.items():
                if name in value and name not in required:
                    walk(child, value[name], f"{path}.{name}" if path else name)

        walk(self.schema, contract, "")

    def missing_requirements(self, contract: dict[str, Any]) -> list[Requirement]:
        out: list[Requirement] = []

        def question_for(child: dict[str, Any], path: str) -> str:
            child = self.resolve_ref(child)
            return (
                child.get("x-acdm-question")
                or child.get("description")
                or f"Podaj wartość dla {path}."
            )

        def walk(node: dict[str, Any], value: Any, path: str) -> None:
            node = self.active_node(node, value)
            node = self.resolve_ref(node)
            if not isinstance(value, dict):
                return
            required = list(node.get("required", []))
            props = node.get("properties", {})
            for name in required:
                child = self.resolve_ref(props.get(name, {}))
                child_path = f"{path}.{name}" if path else name
                if name not in value:
                    if child.get("type") == "object":
                        # Structural objects should have been materialized already.
                        continue
                    out.append(
                        Requirement(
                            path=child_path,
                            question=question_for(child, child_path),
                            value_schema=self.public_schema(child),
                            allowed_values=self.allowed_values(child),
                        )
                    )
                else:
                    child_value = value[name]
                    if isinstance(child_value, dict):
                        walk(child, child_value, child_path)
                    elif isinstance(child_value, list):
                        self._walk_array(child, child_value, child_path, out)
            # Recurse into already-present optional objects too; if activated they can have required children.
            for name, child in props.items():
                if name in required or name not in value:
                    continue
                child_path = f"{path}.{name}" if path else name
                child_value = value[name]
                if isinstance(child_value, dict):
                    walk(child, child_value, child_path)
                elif isinstance(child_value, list):
                    self._walk_array(child, child_value, child_path, out)

        walk(self.schema, contract, "")
        return self._dedupe(out)

    def _walk_array(self, node: dict[str, Any], value: list[Any], path: str, out: list[Requirement]) -> None:
        node = self.resolve_ref(node)
        item_schema = node.get("items")
        if not item_schema:
            return
        for idx, item in enumerate(value):
            item_schema_resolved = self.resolve_ref(item_schema)
            if isinstance(item, dict):
                self._walk_object_item(item_schema_resolved, item, f"{path}.{idx}", out)

    def _walk_object_item(self, node: dict[str, Any], value: dict[str, Any], path: str, out: list[Requirement]) -> None:
        node = self.active_node(node, value)
        required = list(node.get("required", []))
        props = node.get("properties", {})
        for name in required:
            child = self.resolve_ref(props.get(name, {}))
            child_path = f"{path}.{name}"
            if name not in value:
                out.append(
                    Requirement(
                        path=child_path,
                        question=child.get("x-acdm-question") or child.get("description") or f"Podaj wartość dla {child_path}.",
                        value_schema=self.public_schema(child),
                        allowed_values=self.allowed_values(child),
                    )
                )

    @staticmethod
    def _dedupe(items: Iterable[Requirement]) -> list[Requirement]:
        seen: set[str] = set()
        out: list[Requirement] = []
        for item in items:
            if item.path not in seen:
                seen.add(item.path)
                out.append(item)
        return out

    @staticmethod
    def public_schema(node: dict[str, Any]) -> dict[str, Any]:
        keep = {"type", "enum", "const", "pattern", "minimum", "maximum", "minLength", "maxLength", "minItems", "description", "examples", "format"}
        return {k: deepcopy(v) for k, v in node.items() if k in keep}

    @staticmethod
    def allowed_values(node: dict[str, Any]) -> list[Any] | None:
        if "enum" in node:
            return list(node["enum"])
        if "const" in node:
            return [node["const"]]
        return None


    def validate_value(self, node: dict[str, Any], value: Any) -> list[ValidationIssue]:
        wrapper = deepcopy(node)
        wrapper.setdefault("$schema", self.schema.get("$schema", "https://json-schema.org/draft/2020-12/schema"))
        if "$defs" not in wrapper and "$defs" in self.schema:
            wrapper["$defs"] = deepcopy(self.schema["$defs"])
        issues: list[ValidationIssue] = []
        for err in Draft202012Validator(wrapper).iter_errors(value):
            path = ".".join(str(p) for p in err.absolute_path)
            issues.append(ValidationIssue(path=path, message=err.message, validator=err.validator))
        return issues

    def validate(self, contract: dict[str, Any]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for err in sorted(self.validator.iter_errors(contract), key=lambda e: list(e.absolute_path)):
            path = ".".join(str(p) for p in err.absolute_path)
            issues.append(ValidationIssue(path=path, message=err.message, validator=err.validator))
        return issues
