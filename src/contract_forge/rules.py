from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from .models import AppliedValue, Origin, RuleIssue
from .path_utils import get_path, has_path, set_path
from .schema import SchemaNavigator

_MISSING = object()


class RuleEngine:
    def __init__(self, rules: dict[str, Any], schema: SchemaNavigator, deploy_env: str = "dev"):
        self.rules = rules
        self.schema = schema
        self.deploy_env = deploy_env

    @property
    def systems(self) -> list[str]:
        return sorted(self.rules.get("systems", {}).keys())

    def source_types(self, system: str) -> list[str]:
        return list(self.rules.get("systems", {}).get(system, {}).get("source_types", []))

    def apply_system_source_type(
        self,
        contract: dict[str, Any],
        origins: dict[str, Origin],
        system: str,
    ) -> list[AppliedValue]:
        source_types = self.source_types(system)
        if len(source_types) != 1 or has_path(contract, "source.sourceType"):
            return []
        set_path(contract, "source.sourceType", source_types[0])
        origins["source.sourceType"] = Origin.SYSTEM_ENRICHMENT
        return [AppliedValue(path="source.sourceType", value=source_types[0], origin=Origin.SYSTEM_ENRICHMENT, rule_id=f"{system}.source_type")]

    def apply_pass(
        self,
        contract: dict[str, Any],
        origins: dict[str, Origin],
        system: str,
        scope: Origin,
    ) -> tuple[list[AppliedValue], list[RuleIssue]]:
        if scope == Origin.SYSTEM_ENRICHMENT:
            rules = self.rules.get("systems", {}).get(system, {}).get("rules", [])
        elif scope == Origin.GENERIC_ENRICHMENT:
            rules = self.rules.get("defaults", {}).get("rules", [])
        else:
            raise ValueError(scope)

        applied: list[AppliedValue] = []
        issues: list[RuleIssue] = []
        for rule in rules:
            result, issue = self._apply_rule(contract, origins, rule, scope)
            if result:
                applied.extend(result)
            if issue:
                issues.append(issue)
        return applied, issues

    def _apply_rule(
        self,
        contract: dict[str, Any],
        origins: dict[str, Origin],
        rule: dict[str, Any],
        scope: Origin,
    ) -> tuple[list[AppliedValue], RuleIssue | None]:
        rule_id = str(rule.get("id", "<unnamed>"))
        action = rule.get("action")
        path = rule.get("path")

        if not self._condition_matches(contract, rule):
            return [], None

        if action in {"set_default", "copy_value", "format_value", "derive_target_columns"}:
            if not path:
                return [], RuleIssue(rule_id=rule_id, reason="Rule has no target path")
            if not self.schema.path_exists_in_schema(path, contract):
                return [], RuleIssue(rule_id=rule_id, path=path, reason="Target path does not exist in active contract schema")

        if action == "set_default":
            if has_path(contract, path):
                return [], None
            return self._set(contract, origins, path, deepcopy(rule.get("value")), scope, rule_id), None

        if action == "copy_value":
            if has_path(contract, path):
                return [], None
            source_path = rule.get("source_path")
            if not source_path or not has_path(contract, source_path):
                fallback = rule.get("fallback_source_path")
                if not fallback or not has_path(contract, fallback):
                    return [], None
                source_path = fallback
            value = deepcopy(get_path(contract, source_path))
            value = self._transform(value, rule.get("transform"))
            return self._set(contract, origins, path, value, scope, rule_id), None

        if action == "format_value":
            if has_path(contract, path):
                return [], None
            source = None
            source_path = rule.get("source_path")
            if source_path and has_path(contract, source_path):
                source = get_path(contract, source_path)
            elif rule.get("fallback_source_path") and has_path(contract, rule["fallback_source_path"]):
                source = get_path(contract, rule["fallback_source_path"])
            value = self._render(str(rule.get("template", "")), source)
            value = self._transform(value, rule.get("transform"))
            return self._set(contract, origins, path, value, scope, rule_id), None

        if action == "derive_target_columns":
            if has_path(contract, path):
                return [], None
            source_path = rule.get("source_path")
            if not source_path or not has_path(contract, source_path):
                return [], None
            source_columns = get_path(contract, source_path)
            if not isinstance(source_columns, list) or not source_columns:
                return [], None
            columns: list[dict[str, Any]] = []
            for col in source_columns:
                if not isinstance(col, dict) or "name" not in col or "dataType" not in col:
                    return [], None
                target: dict[str, Any] = {
                    "name": col["name"],
                    "dataType": col["dataType"],
                    "mode": "NULLABLE" if col.get("nullable", True) else "REQUIRED",
                    "sourcePath": f"source.columns.{col['name']}",
                }
                columns.append(target)
            return self._set(contract, origins, path, columns, scope, rule_id), None

        return [], RuleIssue(rule_id=rule_id, path=path, reason=f"Unsupported action: {action}")

    def _condition_matches(self, contract: dict[str, Any], rule: dict[str, Any]) -> bool:
        when_path = rule.get("when_path")
        if not when_path:
            return True
        if not has_path(contract, when_path):
            return False
        if "when_value" in rule:
            return get_path(contract, when_path) == rule["when_value"]
        return True

    def _render(self, template: str, source: Any) -> str:
        value = template
        value = re.sub(r"\{\{\s*(?:var\.value\.)?env\s*\}\}", self.deploy_env, value)
        if source is not None:
            value = value.replace("{source}", str(source))
        return value

    @staticmethod
    def _transform(value: Any, transform: str | None) -> Any:
        if transform == "lower" and isinstance(value, str):
            return value.lower()
        if transform == "upper" and isinstance(value, str):
            return value.upper()
        return value

    @staticmethod
    def _set(
        contract: dict[str, Any],
        origins: dict[str, Origin],
        path: str,
        value: Any,
        scope: Origin,
        rule_id: str,
    ) -> list[AppliedValue]:
        set_path(contract, path, value)
        origins[path] = scope
        return [AppliedValue(path=path, value=deepcopy(value), origin=scope, rule_id=rule_id)]
