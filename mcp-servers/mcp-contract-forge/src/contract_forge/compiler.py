from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from jsonschema import Draft202012Validator
from pydantic import BaseModel, ConfigDict

from .contracts import ContractSourcePort
from .schema import SchemaNavigator

ViolationStatus = Literal["missing", "invalid", "forbidden"]


# ``kind`` never defines the logic of a rule; the logic lives in condition/assertion.
# It only names the consequence of a violation. Kinds mapped to ``None`` carry no
# executable semantics here: required/dependency duplicate standard JSON Schema and are
# delegated to Draft202012Validator, registry_lookup names its registry only in prose.
KIND_VIOLATION_STATUS: dict[str, ViolationStatus | None] = {
    "conditional_required": "missing",
    "at_least_one": "missing",
    "conditional_forbidden": "forbidden",
    "cross_field": "invalid",
    "computed_consistency": "invalid",
    "reference_integrity": "invalid",
    "required": None,
    "dependency": None,
    "registry_lookup": None,
}

# The single source of truth for what the rule DSL can express. The definition
# validator rejects anything else instead of guessing it from ``message``.
SUPPORTED_OPERATORS = frozenset(
    {
        "anyOf",
        "equals",
        "equalsPath",
        "exists",
        "existsIn",
        "formula",
        "gtPath",
        "gtePath",
        "notEquals",
        "notIn",
    }
)

# ``path`` is an operand shared by the operators above, not an operator itself.
_OPERAND_KEYS = frozenset({"path"})

# Operators whose value is itself a path into the rule context.
_PATH_VALUED_OPERATORS = frozenset({"equalsPath", "existsIn", "gtPath", "gtePath", "notIn"})


class ContractRule(BaseModel):
    """Parsed ``x-contract-rule``.

    Unknown fields are preserved because the schema DSL can grow independently from
    Contract Forge. Execution stays limited to explicitly supported kinds/operators;
    anything else is rejected by :func:`compile_contract`, not silently interpreted.
    """

    model_config = ConfigDict(extra="allow")

    id: str
    kind: str
    message: str = ""
    path: str | None = None
    severity: str = "error"
    condition: dict[str, Any] | None = None
    assertion: dict[str, Any] | None = None
    source: dict[str, Any] | None = None
    notes: str | None = None


class ContractDefinitionError(Exception):
    """The contract definition itself cannot be executed by this Forge build.

    This is a configuration error, not a user-session error: the contract version is
    NOT READY and the service refuses to serve sessions from it. It must never be
    reported as an invalid user contract.
    """

    def __init__(self, problems: list[str]):
        self.problems = list(problems)
        detail = "\n".join(f"  - {problem}" for problem in self.problems)
        super().__init__(
            f"Contract definition cannot be executed by Contract Forge "
            f"({len(self.problems)} problem(s)):\n{detail}"
        )


@dataclass(frozen=True)
class ContractDefinitionDiagnostic:
    """Non-fatal observation about the contract definition."""

    rule_id: str
    pointer: str
    severity: str
    message: str


@dataclass(frozen=True)
class CompiledRule:
    """A rule that passed definition validation and is ready to be evaluated."""

    rule: ContractRule
    pointer: str
    violation_status: ViolationStatus | None

    @property
    def executable(self) -> bool:
        return self.violation_status is not None and self.rule.assertion is not None


@dataclass(frozen=True)
class CompiledContract:
    """An accepted contract definition. The rule engine works only on this."""

    schema: dict[str, Any]
    navigator: SchemaNavigator
    rules_by_id: dict[str, CompiledRule] = field(default_factory=dict)
    diagnostics: list[ContractDefinitionDiagnostic] = field(default_factory=list)


def compile_contract(source: ContractSourcePort) -> CompiledContract:
    """Load, validate and compile a contract definition.

    Every problem is collected before raising so a broken contract can be repaired in
    one pass instead of one error per run. Rules are validated even when their runtime
    ``condition`` is not active yet: a user must not walk fifteen conversation turns
    only to learn that Forge cannot execute this contract.
    """
    schema = source.load_contract()
    Draft202012Validator.check_schema(schema)
    navigator = SchemaNavigator(schema)

    problems: list[str] = []
    diagnostics: list[ContractDefinitionDiagnostic] = []
    rules_by_id: dict[str, CompiledRule] = {}

    for pointer, raw_rule in _iter_raw_rules(schema):
        try:
            rule = ContractRule.model_validate(raw_rule)
        except Exception as exc:
            problems.append(f"{pointer}: cannot parse x-contract-rule: {exc}")
            continue

        if rule.id in rules_by_id:
            problems.append(
                f"{pointer}: duplicate x-contract-rule id {rule.id!r} "
                f"(already defined at {rules_by_id[rule.id].pointer})"
            )
            continue

        if rule.kind not in KIND_VIOLATION_STATUS:
            problems.append(
                f"{pointer}: unknown x-contract-rule kind {rule.kind!r} "
                f"(known: {', '.join(sorted(KIND_VIOLATION_STATUS))})"
            )
            continue

        rule_problems: list[str] = []
        for label, expression in (("condition", rule.condition), ("assertion", rule.assertion)):
            if expression is not None:
                rule_problems.extend(
                    f"{pointer}: {label}: {problem}"
                    for problem in _validate_expression(expression)
                )
        if rule_problems:
            problems.extend(rule_problems)
            continue

        violation_status = KIND_VIOLATION_STATUS[rule.kind]
        compiled = CompiledRule(rule=rule, pointer=pointer, violation_status=violation_status)
        rules_by_id[rule.id] = compiled
        diagnostics.extend(_path_diagnostics(navigator, schema, compiled))

    if problems:
        raise ContractDefinitionError(problems)

    return CompiledContract(
        schema=schema,
        navigator=navigator,
        rules_by_id=rules_by_id,
        diagnostics=diagnostics,
    )


def _iter_raw_rules(node: Any, pointer: str = "") -> list[tuple[str, Any]]:
    """Collect every ``x-contract-rules`` entry in the document, reachable or not.

    Definition validation covers the whole document: a rule attached to a ``$defs``
    node that no property references yet still has to be executable before the
    contract is accepted.
    """
    found: list[tuple[str, Any]] = []
    if isinstance(node, dict):
        raw_rules = node.get("x-contract-rules")
        if isinstance(raw_rules, list):
            for index, raw_rule in enumerate(raw_rules):
                found.append((f"{pointer}/x-contract-rules/{index}", raw_rule))
        for key, child in node.items():
            if key == "x-contract-rules":
                continue
            found.extend(_iter_raw_rules(child, f"{pointer}/{_escape(key)}"))
    elif isinstance(node, list):
        for index, child in enumerate(node):
            found.extend(_iter_raw_rules(child, f"{pointer}/{index}"))
    return found


def _escape(key: str) -> str:
    return key.replace("~", "~0").replace("/", "~1")


def _validate_expression(expression: Any) -> list[str]:
    """Reject any operator the engine cannot execute, recursing through ``anyOf``."""
    if not isinstance(expression, dict):
        return [f"expected an object, got {type(expression).__name__}"]

    problems: list[str] = []
    operators = set(expression) - _OPERAND_KEYS
    unknown = sorted(operators - SUPPORTED_OPERATORS)
    if unknown:
        problems.append(
            f"unsupported operator(s) {', '.join(repr(name) for name in unknown)} "
            f"(supported: {', '.join(sorted(SUPPORTED_OPERATORS))})"
        )
    if not operators:
        problems.append("no operator present")

    children = expression.get("anyOf")
    if "anyOf" in expression:
        if not isinstance(children, list) or not children:
            problems.append("anyOf must be a non-empty list")
        else:
            for index, child in enumerate(children):
                problems.extend(f"anyOf[{index}]: {problem}" for problem in _validate_expression(child))
    return problems


def _path_diagnostics(
    navigator: SchemaNavigator,
    schema: dict[str, Any],
    compiled: CompiledRule,
) -> list[ContractDefinitionDiagnostic]:
    """Warn about rule operands that cannot resolve against the schema node.

    An unresolvable path makes the rule permanently inert rather than wrong, so it is
    reported instead of rejected: `$defs` that are still placeholders are a normal
    intermediate state of a growing contract.
    """
    node = _node_at_pointer(schema, compiled.pointer)
    if node is None:
        return []
    node = navigator.resolve_ref(node)

    diagnostics: list[ContractDefinitionDiagnostic] = []
    for path in sorted(_operand_paths(compiled.rule)):
        if _static_path_exists(navigator, node, path):
            continue
        diagnostics.append(
            ContractDefinitionDiagnostic(
                rule_id=compiled.rule.id,
                pointer=compiled.pointer,
                severity="warning",
                message=(
                    f"Rule path {path!r} does not resolve against the schema node it is "
                    f"attached to; the rule stays inert."
                ),
            )
        )
    return diagnostics


def _node_at_pointer(schema: dict[str, Any], pointer: str) -> dict[str, Any] | None:
    """Resolve the schema node that owns a rule (the pointer minus its rule suffix)."""
    parts = [part for part in pointer.split("/") if part]
    if len(parts) < 2 or parts[-2] != "x-contract-rules":
        return None
    current: Any = schema
    for part in parts[:-2]:
        key = part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and key in current:
            current = current[key]
        elif isinstance(current, list) and key.isdigit() and int(key) < len(current):
            current = current[int(key)]
        else:
            return None
    return current if isinstance(current, dict) else None


def _operand_paths(rule: ContractRule) -> set[str]:
    paths: set[str] = set()
    if rule.path:
        paths.add(rule.path)
    for expression in (rule.condition, rule.assertion):
        paths.update(_expression_paths(expression))
    return paths


def _expression_paths(expression: Any) -> set[str]:
    if not isinstance(expression, dict):
        return set()
    paths: set[str] = set()
    value = expression.get("path")
    if isinstance(value, str):
        paths.add(value)
    for operator in _PATH_VALUED_OPERATORS:
        operand = expression.get(operator)
        if isinstance(operand, str):
            paths.add(operand)
    for child in expression.get("anyOf", []) or []:
        paths.update(_expression_paths(child))
    return paths


def _static_path_exists(navigator: SchemaNavigator, node: dict[str, Any], path: str) -> bool:
    """Walk a dotted rule path through the schema without a contract instance.

    ``oneOf`` cannot be narrowed without a value here, so every branch is tried and a
    hit in any of them counts.
    """
    parts = [part for part in path.split(".") if part]
    candidates = [node]
    for part in parts:
        key = part[:-3] if part.endswith("[*]") else part
        next_candidates: list[dict[str, Any]] = []
        for base in candidates:
            for branch in _expand_branches(navigator, base):
                properties = branch.get("properties")
                if isinstance(properties, dict) and key in properties:
                    child = properties[key]
                    if isinstance(child, dict):
                        next_candidates.append(navigator.resolve_ref(child))
                elif branch.get("additionalProperties") is True:
                    # An open object accepts any key; the path is expressible.
                    next_candidates.append({})
        if not next_candidates:
            return False
        candidates = next_candidates
    return True


def _expand_branches(navigator: SchemaNavigator, candidate: dict[str, Any]) -> list[dict[str, Any]]:
    resolved = navigator.resolve_ref(candidate)
    branches = [resolved]
    for branch in resolved.get("oneOf", []) or []:
        if isinstance(branch, dict):
            branches.append(navigator.resolve_ref(branch))
    items = resolved.get("items")
    if isinstance(items, dict):
        branches.append(navigator.resolve_ref(items))
    return branches
