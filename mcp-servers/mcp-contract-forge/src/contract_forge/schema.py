from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Iterator

from jsonschema import Draft202012Validator

from .models import AppliedValue, Origin, Requirement, ValidationIssue
from .path_utils import get_path, has_path, write_value


UNSUPPORTED_REQUIREMENT_KEYWORDS = frozenset(
    {
        "allOf",
        "anyOf",
        "contains",
        "dependentRequired",
        "dependentSchemas",
        "else",
        "if",
        "not",
        "oneOf",
        "prefixItems",
        "then",
        "unevaluatedItems",
    }
)


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
        node = deepcopy(node)
        for _ in range(8):
            if "$ref" not in node:
                break
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

    def requirement_at_path(self, path: str, contract: dict[str, Any]) -> Requirement | None:
        """Describe an active-schema path with the same metadata as a pending field."""
        return self.requirement_for_path(path, contract)

    def requirement_for_path(
        self,
        path: str,
        contract: dict[str, Any],
        *,
        status: str = "missing",
        reason: str = "required",
        rule_id: str | None = None,
        message: str | None = None,
        fallback_question: str | None = None,
    ) -> Requirement | None:
        """Build a requirement for an active-schema path, whatever discovered it.

        The schema still supplies question/value_schema/allowed_values; the caller only
        supplies provenance, so a rule-driven requirement is indistinguishable from a
        schema-driven one on the ADCM side except for ``reason``/``rule_id``.
        """
        node = self.schema_at_path(path, contract)
        if node is None:
            return None
        return Requirement(
            path=path,
            status=status,
            reason=reason,
            rule_id=rule_id,
            message=message,
            question=(
                node.get("x-acdm-question")
                or node.get("description")
                or fallback_question
                or f"Podaj wartość dla {path}."
            ),
            value_schema=self.public_schema(node),
            unsupported_schema_keywords=self.unsupported_requirement_keywords(node),
            allowed_values=self.allowed_values(node),
        )

    def iter_contract_rule_bindings(
        self,
        contract: dict[str, Any],
    ) -> Iterator[tuple[str, Any, dict[str, Any]]]:
        """Yield ``(base_path, context_value, raw_rule)`` for active schema nodes.

        Rules are bound to the runtime location of the schema definition, so paths
        inside condition/assertion are relative to that location. Only nodes present in
        the current contract are evaluated; an absent optional section has no active
        business-rule context yet.
        """

        def walk(node: dict[str, Any], value: Any, path: str) -> Iterator[tuple[str, Any, dict[str, Any]]]:
            node = self.active_node(node, value)
            raw_rules = node.get("x-contract-rules", [])
            if isinstance(raw_rules, list):
                for raw_rule in raw_rules:
                    if isinstance(raw_rule, dict):
                        yield path, value, deepcopy(raw_rule)

            if isinstance(value, dict):
                props = node.get("properties", {})
                for name, child_value in value.items():
                    child_schema = props.get(name)
                    if not isinstance(child_schema, dict):
                        continue
                    child_path = f"{path}.{name}" if path else name
                    yield from walk(child_schema, child_value, child_path)
            elif isinstance(value, list):
                item_schema = node.get("items")
                if isinstance(item_schema, dict):
                    for idx, item in enumerate(value):
                        child_path = f"{path}.{idx}" if path else str(idx)
                        yield from walk(item_schema, item, child_path)

        yield from walk(self.schema, contract, "")

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

    def inject_defaults(self, contract: dict[str, Any], origins: dict[str, Origin]) -> list[AppliedValue]:
        applied: list[AppliedValue] = []

        def walk(node: dict[str, Any], value: Any, path: str, active: bool = True) -> None:
            node = self.active_node(node, value)
            node = self.resolve_ref(node)
            typ = node.get("type")
            if isinstance(value, dict):
                for name, child in node.get("properties", {}).items():
                    child = self.resolve_ref(child)
                    child_path = f"{path}.{name}" if path else name
                    if name not in value and "default" in child:
                        result = write_value(
                            contract,
                            origins,
                            child_path,
                            child["default"],
                            Origin.SCHEMA_DEFAULT,
                        )
                        if result:
                            applied.append(result)
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
                    write_value(contract, origins, child_path, {}, Origin.STRUCTURAL)
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
                            unsupported_schema_keywords=self.unsupported_requirement_keywords(child),
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
        return self.dedupe_requirements(out)

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
                        unsupported_schema_keywords=self.unsupported_requirement_keywords(child),
                        allowed_values=self.allowed_values(child),
                    )
                )

    @staticmethod
    def dedupe_requirements(items: Iterable[Requirement]) -> list[Requirement]:
        """Keep the first requirement per path; discovery sources may overlap."""
        seen: set[str] = set()
        out: list[Requirement] = []
        for item in items:
            if item.path not in seen:
                seen.add(item.path)
                out.append(item)
        return out

    def public_schema(self, node: dict[str, Any], *, depth: int = 2) -> dict[str, Any]:
        """Return the small schema fragment ADCM needs to normalize candidates.

        Stage 04 needs one structural level for ``array<object>`` requirements. This
        is intentionally not a second JSON Schema engine or a full schema export.
        """
        node = self.active_node(node)
        keep = {
            "type",
            "enum",
            "const",
            "pattern",
            "minimum",
            "maximum",
            "minLength",
            "maxLength",
            "minItems",
            "description",
            "examples",
            "format",
        }
        public = {key: deepcopy(value) for key, value in node.items() if key in keep}
        if depth <= 0:
            return public

        if node.get("type") == "array" and isinstance(node.get("items"), dict):
            public["items"] = self.public_schema(node["items"], depth=depth - 1)
        if node.get("type") == "object":
            required = node.get("required")
            if isinstance(required, list):
                public["required"] = deepcopy(required)
            properties = node.get("properties")
            if isinstance(properties, dict):
                public["properties"] = {
                    name: self.public_schema(child, depth=depth - 1)
                    for name, child in properties.items()
                    if isinstance(child, dict)
                }
        return public

    def unsupported_requirement_keywords(
        self,
        node: dict[str, Any],
        *,
        depth: int = 2,
    ) -> list[str]:
        """Report schema constructs ADCM must not interpret for this requirement."""
        found: set[str] = set()

        def walk(candidate: dict[str, Any], remaining: int) -> None:
            candidate = self.active_node(candidate)
            found.update(UNSUPPORTED_REQUIREMENT_KEYWORDS.intersection(candidate))
            if remaining <= 0:
                return
            if candidate.get("type") == "array" and isinstance(candidate.get("items"), dict):
                walk(candidate["items"], remaining - 1)
            if candidate.get("type") == "object":
                for child in candidate.get("properties", {}).values():
                    if isinstance(child, dict):
                        walk(child, remaining - 1)

        walk(node, depth)
        return sorted(found)

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
