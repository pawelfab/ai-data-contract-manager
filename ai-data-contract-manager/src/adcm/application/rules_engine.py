import re
from typing import Any

from adcm.domain.contract import ContractState
from adcm.domain.forge import ForgeAnalysis
from adcm.domain.proposals import Proposal, ProposalMode
from adcm.domain.provenance import ValueSource
from adcm.domain.rules import ConventionRule, RuleCondition, RuleScope, RulesDocument

from .json_pointer import exists, get

_POINTER_TEMPLATE = re.compile(r"\{(/[^{}]+)\}")


class ConventionRulesEngine:
    def evaluate(self, rules: RulesDocument, state: ContractState, forge: ForgeAnalysis) -> list[Proposal]:
        document = state.document
        current_system = self._read_optional(document, rules.systemSelectorPath)
        proposals: list[Proposal] = []
        for rule in rules.rules:
            if rule.scope == RuleScope.SYSTEM:
                if current_system is None or rule.system is None or str(current_system).lower() != rule.system.lower():
                    continue
            if not self._conditions_match(rule, state, forge):
                continue
            rendered, dependencies = self._render_value(rule.value, document)
            proposals.append(
                Proposal(
                    id=f"rule:{rule.id}",
                    path=rule.path,
                    value=rendered,
                    source=ValueSource.USER_RULE if rule.scope == RuleScope.USER else ValueSource.APP_RULE,
                    producer_id=rule.id,
                    priority=rule.priority,
                    specificity={RuleScope.GLOBAL: 0, RuleScope.SYSTEM: 10, RuleScope.USER: 20}[rule.scope],
                    reason=f"ux rule {rule.id}",
                    derived_from=sorted(set(dependencies + self._condition_dependencies(rule))),
                    mode=ProposalMode.ENSURE_PRESENT if rendered == {} or rendered == [] else ProposalMode.SET,
                )
            )
        return proposals

    def _conditions_match(self, rule: ConventionRule, state: ContractState, forge: ForgeAnalysis) -> bool:
        if rule.when is None:
            return True
        conditions = rule.when if isinstance(rule.when, list) else [rule.when]
        return all(self._condition_matches(rule, condition, state, forge) for condition in conditions)

    def _condition_matches(self, rule: ConventionRule, condition: RuleCondition, state: ContractState, forge: ForgeAnalysis) -> bool:
        document = state.document
        present = exists(document, condition.path)
        if condition.exists is not None and present != condition.exists:
            # Legacy ux_rules often use `target exists=false` only as an application guard.
            # Once this exact rule produced the target, keep the rule declaratively active.
            provenance = state.provenance.get(rule.path)
            self_guard_satisfied = (
                condition.path == rule.path
                and condition.exists is False
                and present
                and provenance is not None
                and provenance.producer_id == rule.id
            )
            if not self_guard_satisfied:
                return False
        if "equals" in condition.model_fields_set:
            if not present or get(document, condition.path) != condition.equals:
                return False
        if condition.requirementsComplete is not None:
            prefix = condition.path.rstrip("/") + "/"
            incomplete = any(item.path == condition.path or item.path.startswith(prefix) for item in forge.missing)
            complete = not incomplete
            if complete != condition.requirementsComplete:
                return False
        return True

    def _render_value(self, value: Any, document: dict) -> tuple[Any, list[str]]:
        if not isinstance(value, str):
            return value, []
        dependencies: list[str] = []
        exact = _POINTER_TEMPLATE.fullmatch(value)
        if exact:
            pointer = exact.group(1)
            dependencies.append(pointer)
            return get(document, pointer), dependencies

        def replace(match: re.Match[str]) -> str:
            pointer = match.group(1)
            dependencies.append(pointer)
            return str(get(document, pointer))

        return _POINTER_TEMPLATE.sub(replace, value), dependencies

    @staticmethod
    def _condition_dependencies(rule: ConventionRule) -> list[str]:
        if rule.when is None:
            return []
        conditions = rule.when if isinstance(rule.when, list) else [rule.when]
        return [condition.path for condition in conditions]

    @staticmethod
    def _read_optional(document: dict, path: str):
        try:
            return get(document, path)
        except KeyError:
            return None
