from __future__ import annotations

import hashlib
import json
from typing import Any

from .models import ContractState, RequirementsCatalogue


def document_fingerprint(value: Any) -> str:
    canonical = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def get_path(document: dict[str, Any], path: str) -> Any:
    current: Any = document
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def has_value(document: dict[str, Any], path: str) -> bool:
    value = get_path(document, path)
    return value is not None and value != "" and value != [] and value != {}


def set_path(document: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    current = document
    for part in parts[:-1]:
        next_value = current.get(part)
        if not isinstance(next_value, dict):
            next_value = {}
            current[part] = next_value
        current = next_value
    current[parts[-1]] = value


def delete_path(document: dict[str, Any], path: str) -> None:
    parts = path.split(".")
    current: Any = document
    parents: list[tuple[dict[str, Any], str]] = []
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            return
        parents.append((current, part))
        current = current[part]
    if not isinstance(current, dict):
        return
    current.pop(parts[-1], None)
    for parent, key in reversed(parents):
        child = parent.get(key)
        if isinstance(child, dict) and not child:
            parent.pop(key)
        else:
            break


def activate_scope(
    state: ContractState, requirements: RequirementsCatalogue
) -> None:
    source_changed = (
        state.source_type is not None
        and state.source_type != requirements.source_type
    )
    if source_changed or not isinstance(state.draft.get("source"), dict):
        state.draft["source"] = {}
    state.draft["source"]["sourceType"] = requirements.source_type

    targets = state.draft.get("targets")
    if not isinstance(targets, dict):
        targets = {}
        state.draft["targets"] = targets
    for layer in list(targets):
        if layer not in requirements.target_layers:
            del targets[layer]
    for layer in requirements.target_layers:
        targets.setdefault(layer, {})

    state.source_type = requirements.source_type
    state.target_layers = requirements.target_layers
    state.requirements = requirements
    active_decisions = {
        decision.path for decision in requirements.optional_decisions
    }
    state.optional_decision_choices = {
        path: choice
        for path, choice in state.optional_decision_choices.items()
        if path in active_decisions
    }
    state.revision += 1
    state.automatic_repair_attempts = 0
    state.invalidate_current_result()


def missing_required_paths(state: ContractState) -> list[str]:
    if not state.requirements:
        return ["source.sourceType"]
    return [
        field.path
        for field in state.requirements.field_catalog
        if (
            field.required
            or (
                field.required_if_path is not None
                and (
                    has_value(state.draft, field.required_if_path)
                    or state.optional_decision_choices.get(
                        field.required_if_path
                    )
                    is True
                )
            )
        )
        and not has_value(state.draft, field.path)
    ]


def unresolved_optional_decisions(state: ContractState) -> list[dict[str, Any]]:
    if not state.requirements:
        return []
    return [
        decision.model_dump(mode="json")
        for decision in state.requirements.optional_decisions
        if decision.path not in state.optional_decision_choices
        and not has_value(state.draft, decision.path)
    ]
