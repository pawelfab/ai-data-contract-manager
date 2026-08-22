from __future__ import annotations

import re
from typing import Any, Iterable

from contract_forge.domain.enrichment.models import EnrichmentContext, EnrichmentRule, EnrichmentScope
from contract_forge.domain.evaluation.models import SuggestedValue
from contract_forge.utils.pointer import exists_pointer, get_pointer

_TEMPLATE = re.compile(r"\{(/[^{}]+)\}")
_MISSING = object()


def resolve_enrichment(
    document: dict[str, Any],
    rules: list[EnrichmentRule],
    context: EnrichmentContext,
    *,
    eligible_paths: Iterable[str],
) -> list[SuggestedValue]:
    """Resolve only rules relevant to currently discovered/fillable paths.

    This prevents enrichment from activating optional/later branches ahead of discovery.
    """

    eligible = set(eligible_paths)
    best: dict[str, SuggestedValue] = {}
    for rule in rules:
        if not _scope_matches(rule, context) or not _matches(document, rule):
            continue
        targets = _targets(rule, eligible, document)
        for target in targets:
            value = _resolve_value(rule, document)
            if value is _MISSING:
                continue
            priority = int(rule.scope) * 1000 + rule.priority
            suggestion = SuggestedValue(
                path=target,
                value=value,
                source=_source_name(rule),
                priority=priority,
                sourceRef=rule.source_ref,
                ruleId=rule.id,
            )
            current = best.get(target)
            if current is None or current.priority <= suggestion.priority:
                best[target] = suggestion
    return list(best.values())


def _scope_matches(rule: EnrichmentRule, context: EnrichmentContext) -> bool:
    if rule.scope == EnrichmentScope.SYSTEM:
        return bool(
            context.source_system
            and rule.system
            and context.source_system.casefold() == rule.system.casefold()
        )
    if rule.scope == EnrichmentScope.USER:
        return bool(context.user_id and rule.user_id and context.user_id == rule.user_id)
    return True


def _matches(document: dict[str, Any], rule: EnrichmentRule) -> bool:
    for condition in rule.conditions:
        if condition.exists is not None and exists_pointer(document, condition.path) != condition.exists:
            return False
        if condition.equals is not None and get_pointer(document, condition.path, None) != condition.equals:
            return False
    return True


def _targets(rule: EnrichmentRule, eligible: set[str], document: dict[str, Any]) -> list[str]:
    if rule.path_pattern:
        return sorted(path for path in eligible if _pointer_glob_match(rule.path_pattern, path))
    if not rule.path:
        return []
    # Existing paths remain eligible for recomputation; otherwise only the current discovery set.
    if rule.path in eligible or exists_pointer(document, rule.path):
        return [rule.path]
    return []


def _resolve_value(rule: EnrichmentRule, document: dict[str, Any]):
    if rule.value_from:
        return get_pointer(document, rule.value_from, _MISSING)
    if not isinstance(rule.value, str):
        return rule.value
    matches = list(_TEMPLATE.finditer(rule.value))
    if not matches:
        return rule.value
    if len(matches) == 1 and matches[0].span() == (0, len(rule.value)):
        return get_pointer(document, matches[0].group(1), _MISSING)
    out = rule.value
    for match in matches:
        value = get_pointer(document, match.group(1), _MISSING)
        if value is _MISSING:
            return _MISSING
        out = out.replace(match.group(0), str(value))
    return out


def _pointer_glob_match(pattern: str, pointer: str) -> bool:
    p = _segments(pattern)
    x = _segments(pointer)
    return _glob_segments(p, x)


def _segments(pointer: str) -> list[str]:
    return [] if pointer in {"", "/"} else pointer.strip("/").split("/")


def _glob_segments(pattern: list[str], value: list[str]) -> bool:
    if not pattern:
        return not value
    head = pattern[0]
    if head == "**":
        return _glob_segments(pattern[1:], value) or bool(value) and _glob_segments(pattern, value[1:])
    if not value:
        return False
    if head != "*" and head != value[0]:
        return False
    return _glob_segments(pattern[1:], value[1:])


def _source_name(rule: EnrichmentRule) -> str:
    return {
        EnrichmentScope.GLOBAL: "global_enrichment",
        EnrichmentScope.SYSTEM: "system_enrichment",
        EnrichmentScope.USER: "user_enrichment",
    }.get(rule.scope, "enrichment")
