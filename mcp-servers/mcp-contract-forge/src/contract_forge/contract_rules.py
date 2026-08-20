from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any

from .compiler import CompiledContract, CompiledRule
from .models import ContractRuleIssue, Requirement

_MISSING = object()


class UnsupportedRuleExpression(ValueError):
    """The expression cannot be evaluated against the current contract values."""


@dataclass(frozen=True)
class RuleBinding:
    """One compiled rule bound to the runtime location of its schema node."""

    base_path: str
    context: Any
    compiled: CompiledRule

    def absolute_path(self, relative: str | None) -> str | None:
        if not relative:
            return self.base_path or None
        if not self.base_path:
            return relative
        return f"{self.base_path}.{relative}"


class ContractRuleEngine:
    """Deterministic evaluator for structured ``x-contract-rules``.

    It works only on an already accepted :class:`CompiledContract`, so unknown kinds and
    operators cannot reach it: those are configuration errors raised at load time. At
    runtime a rule either evaluates, is inactive, or is reported as non-executable —
    never guessed from ``message``, ``notes`` or the originating Pydantic validator.
    """

    def __init__(self, compiled: CompiledContract):
        self.compiled = compiled
        self.navigator = compiled.navigator

    def evaluate(self, contract: dict[str, Any]) -> list[ContractRuleIssue]:
        issues: list[ContractRuleIssue] = []
        for base_path, context, raw_rule in self.navigator.iter_contract_rule_bindings(contract):
            compiled = self.compiled.rules_by_id.get(str(raw_rule.get("id", "")))
            if compiled is None:
                # Every rule in the document was compiled; a miss can only mean the
                # instance carries a node the compiler never saw.
                continue
            binding = RuleBinding(base_path=base_path, context=context, compiled=compiled)
            issue = self._evaluate_binding(binding, contract)
            if issue is not None:
                issues.append(issue)
        return issues

    def missing_requirements(
        self,
        contract: dict[str, Any],
        issues: list[ContractRuleIssue] | None = None,
    ) -> list[Requirement]:
        requirements: list[Requirement] = []
        for issue in issues if issues is not None else self.evaluate(contract):
            if issue.status != "missing" or not issue.path:
                continue
            requirement = self.navigator.requirement_for_path(
                issue.path,
                contract,
                status="missing",
                reason="contract_rule",
                rule_id=issue.rule_id,
                message=issue.message,
                fallback_question=issue.message,
            )
            if requirement is not None:
                requirements.append(requirement)
        return self.navigator.dedupe_requirements(requirements)

    @staticmethod
    def blocking_issues(issues: list[ContractRuleIssue]) -> list[ContractRuleIssue]:
        """Issues that must stop completion. Non-executable rules never block."""
        return [
            issue
            for issue in issues
            if issue.status in {"invalid", "forbidden"} and issue.severity == "error"
        ]

    def _evaluate_binding(
        self,
        binding: RuleBinding,
        contract: dict[str, Any],
    ) -> ContractRuleIssue | None:
        rule = binding.compiled.rule

        if binding.compiled.violation_status is None:
            return self._skipped(
                binding,
                f"kind {rule.kind!r} carries no executable semantics; "
                "it is delegated to JSON Schema or not machine-readable",
            )
        if rule.assertion is None:
            return self._skipped(binding, "rule has no structured assertion")

        try:
            if rule.condition is not None and not self._eval_expression(binding.context, rule.condition):
                return None
            satisfied = self._eval_expression(binding.context, rule.assertion)
        except UnsupportedRuleExpression as exc:
            return self._skipped(binding, str(exc))

        if satisfied:
            return None

        status = binding.compiled.violation_status
        path = binding.absolute_path(rule.path or self._primary_expression_path(rule.assertion))

        # A missing value can only become a requirement when ADCM has a schema node to
        # fill. Otherwise the rule is inert; it must not strand the session.
        if status == "missing" and path and not self.navigator.path_exists_in_schema(path, contract):
            return self._skipped(
                binding,
                f"rule target path is not present in the active contract schema: {path}",
                absolute_path=path,
            )

        return ContractRuleIssue(
            rule_id=rule.id,
            status=status,
            path=path,
            message=rule.message or f"x-contract-rule failed: {rule.id}",
            severity=rule.severity,
        )

    def _skipped(
        self,
        binding: RuleBinding,
        detail: str,
        absolute_path: str | None = None,
    ) -> ContractRuleIssue:
        rule = binding.compiled.rule
        return ContractRuleIssue(
            rule_id=rule.id,
            status="skipped_non_executable",
            path=absolute_path or binding.absolute_path(rule.path),
            message=rule.message or f"x-contract-rule not executed: {rule.id}",
            severity=rule.severity,
            detail=detail,
        )

    def _eval_expression(self, context: Any, expr: dict[str, Any]) -> bool:
        if "anyOf" in expr:
            children = expr["anyOf"]
            return any(self._eval_expression(context, child) for child in children)

        path = expr.get("path")

        if "exists" in expr:
            if not isinstance(path, str):
                raise UnsupportedRuleExpression("exists requires path")
            return self._path_exists(context, path) is bool(expr["exists"])

        if "equals" in expr:
            if not isinstance(path, str):
                raise UnsupportedRuleExpression("equals requires path")
            value = self._get_single(context, path)
            return value is not _MISSING and value == expr["equals"]

        if "notEquals" in expr:
            if not isinstance(path, str):
                raise UnsupportedRuleExpression("notEquals requires path")
            value = self._get_single(context, path)
            return value is not _MISSING and value != expr["notEquals"]

        for operator, compare in (("gtePath", _gte), ("gtPath", _gt)):
            if operator not in expr:
                continue
            other = expr[operator]
            if not isinstance(path, str) or not isinstance(other, str):
                raise UnsupportedRuleExpression(f"{operator} requires path and {operator}")
            left = self._get_single(context, path)
            right = self._get_single(context, other)
            if left is _MISSING or right is _MISSING:
                # Incomplete values are handled by ordinary required discovery.
                return True
            try:
                return compare(left, right)
            except TypeError as exc:
                raise UnsupportedRuleExpression(f"{operator} values are not comparable: {exc}") from exc

        if "notIn" in expr:
            if not isinstance(path, str) or not isinstance(expr["notIn"], str):
                raise UnsupportedRuleExpression("notIn requires path and collection path")
            value = self._get_single(context, path)
            if value is _MISSING:
                return True
            return value not in self._get_values(context, expr["notIn"])

        if "existsIn" in expr:
            if not isinstance(path, str) or not isinstance(expr["existsIn"], str):
                raise UnsupportedRuleExpression("existsIn requires path and collection path")
            source_values = self._get_values(context, path)
            if not source_values:
                return True
            target_values = self._get_values(context, expr["existsIn"])
            return all(value in target_values for value in source_values)

        if "formula" in expr and "equalsPath" in expr:
            target_path = expr["equalsPath"]
            if not isinstance(target_path, str) or not isinstance(expr["formula"], str):
                raise UnsupportedRuleExpression("formula equality requires equalsPath and formula strings")
            target = self._get_single(context, target_path)
            if target is _MISSING:
                # The DSL has no autofill operation, so an absent target is not a
                # violation. Inferring one from `message` is exactly what is forbidden.
                return True
            return target == self._eval_formula(context, expr["formula"])

        if "equalsPath" in expr:
            other_path = expr["equalsPath"]
            if not isinstance(path, str) or not isinstance(other_path, str):
                raise UnsupportedRuleExpression("equalsPath requires path and equalsPath")
            left = self._get_single(context, path)
            right = self._get_single(context, other_path)
            if left is _MISSING or right is _MISSING:
                return True
            return left == right

        raise UnsupportedRuleExpression(f"no evaluable operator in {sorted(expr.keys())}")

    @staticmethod
    def _primary_expression_path(expr: dict[str, Any]) -> str | None:
        value = expr.get("path")
        return value if isinstance(value, str) else None

    @staticmethod
    def _path_exists(context: Any, path: str) -> bool:
        return bool(ContractRuleEngine._get_values(context, path))

    @staticmethod
    def _get_single(context: Any, path: str) -> Any:
        values = ContractRuleEngine._get_values(context, path)
        return values[0] if values else _MISSING

    @staticmethod
    def _get_values(context: Any, path: str) -> list[Any]:
        """Resolve a dotted path relative to the rule context; ``[*]`` fans out a list."""
        current = [context]
        for part in (p for p in path.split(".") if p):
            wildcard = part.endswith("[*]")
            key = part[:-3] if wildcard else part
            next_values: list[Any] = []
            for item in current:
                if not isinstance(item, dict) or key not in item:
                    continue
                value = item[key]
                if wildcard:
                    if isinstance(value, list):
                        next_values.extend(value)
                else:
                    next_values.append(value)
            if not next_values:
                return []
            current = next_values
        return current

    def _eval_formula(self, context: Any, formula: str) -> Any:
        """Evaluate a tiny arithmetic expression over contract values.

        Only literals, path names and ``+ - * /`` are allowed; this is not a general
        expression evaluator and never touches Python builtins.
        """
        tree = ast.parse(formula, mode="eval")

        def visit(node: ast.AST) -> Any:
            if isinstance(node, ast.Expression):
                return visit(node.body)
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                return node.value
            if isinstance(node, ast.Name):
                value = self._get_single(context, node.id)
                if value is _MISSING:
                    raise UnsupportedRuleExpression(f"formula variable is missing: {node.id}")
                if not isinstance(value, (int, float)):
                    raise UnsupportedRuleExpression(f"formula variable is not numeric: {node.id}")
                return value
            if isinstance(node, ast.BinOp):
                left = visit(node.left)
                right = visit(node.right)
                if isinstance(node.op, ast.Add):
                    return left + right
                if isinstance(node.op, ast.Sub):
                    return left - right
                if isinstance(node.op, ast.Mult):
                    return left * right
                if isinstance(node.op, ast.Div):
                    return left / right
                raise UnsupportedRuleExpression(f"unsupported formula operator: {type(node.op).__name__}")
            if isinstance(node, ast.UnaryOp):
                value = visit(node.operand)
                if isinstance(node.op, ast.USub):
                    return -value
                if isinstance(node.op, ast.UAdd):
                    return value
            raise UnsupportedRuleExpression(f"unsupported formula syntax: {type(node).__name__}")

        return visit(tree)


def _gte(left: Any, right: Any) -> bool:
    return left >= right


def _gt(left: Any, right: Any) -> bool:
    return left > right
