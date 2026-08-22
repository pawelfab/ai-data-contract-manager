from __future__ import annotations

from copy import deepcopy

from contract_forge.application.services.schema_paths import pointer_exists_in_schema
from contract_forge.application.services.semantic_path_resolver import SemanticPathResolver, UnknownSemanticPath
from contract_forge.domain.contract.models import ContractSemanticPaths
from contract_forge.domain.discovery.models import (
    DiscoveryOutcome,
    DiscoveryPolicy,
    DiscoveryPolicyIssue,
)
from contract_forge.domain.evaluation.models import Requirement
from contract_forge.utils.pointer import exists_pointer


class RequirementDiscovery:
    def __init__(
        self,
        policy: DiscoveryPolicy,
        paths: ContractSemanticPaths,
        raw_schema: dict,
        *,
        strict: bool = False,
    ):
        self.policy = policy
        self.paths = paths
        self.raw_schema = raw_schema
        self.strict = strict
        self.semantic = SemanticPathResolver()

    def discover(self, *, document: dict, requirements: list[Requirement]) -> DiscoveryOutcome:
        if not self.policy.steps:
            return DiscoveryOutcome(requirements=requirements)

        issues = self._validate_policy()
        if issues and self.strict:
            raise ValueError("Invalid discovery policy: " + "; ".join(i.message for i in issues))

        selected = None
        for step in self.policy.steps:
            try:
                present = [self.semantic.resolve(x, self.paths) for x in step.when_present]
                missing_all = [self.semantic.resolve(x, self.paths) for x in step.when_missing]
                missing_any = [self.semantic.resolve(x, self.paths) for x in step.when_any_missing]
            except UnknownSemanticPath as exc:
                issues.append(DiscoveryPolicyIssue(step_id=step.id, message=str(exc)))
                continue

            if present and not all(exists_pointer(document, p) for p in present):
                continue
            if missing_all and not all(not exists_pointer(document, p) for p in missing_all):
                continue
            if missing_any and not any(not exists_pointer(document, p) for p in missing_any):
                continue
            selected = step
            break

        if selected is None:
            return DiscoveryOutcome(requirements=requirements, issues=issues)

        if selected.expose_matching_schema_requirements:
            visible = list(requirements)
        else:
            try:
                exposed = {self.semantic.resolve(x, self.paths) for x in selected.expose}
            except UnknownSemanticPath as exc:
                issues.append(DiscoveryPolicyIssue(step_id=selected.id, message=str(exc)))
                exposed = set()
            visible = [r for r in requirements if r.path in exposed]
            if requirements and not visible:
                issue = DiscoveryPolicyIssue(
                    step_id=selected.id,
                    message=(
                        f"Discovery step {selected.id!r} exposed no current fillable requirements; "
                        "falling back to the full fillable set."
                    ),
                )
                issues.append(issue)
                if self.strict:
                    raise ValueError(issue.message)
                visible = list(requirements)

        return DiscoveryOutcome(
            requirements=[self._with_presentation(r) for r in visible],
            issues=issues,
        )

    def _with_presentation(self, requirement: Requirement) -> Requirement:
        result = requirement.model_copy(deep=True)
        for key, presentation in self.policy.presentation.items():
            try:
                path = self.semantic.resolve(key, self.paths)
            except UnknownSemanticPath:
                continue
            if path != requirement.path:
                continue
            if presentation.display_name:
                result.display_name = presentation.display_name
            if presentation.help_text:
                result.help_text = presentation.help_text
            break
        return result

    def _validate_policy(self) -> list[DiscoveryPolicyIssue]:
        issues: list[DiscoveryPolicyIssue] = []
        for step in self.policy.steps:
            for raw_path in step.when_present + step.when_missing + step.when_any_missing + step.expose:
                try:
                    path = self.semantic.resolve(raw_path, self.paths)
                except UnknownSemanticPath as exc:
                    issues.append(DiscoveryPolicyIssue(step_id=step.id, path=raw_path, message=str(exc)))
                    continue
                if not pointer_exists_in_schema(self.raw_schema, path):
                    issues.append(
                        DiscoveryPolicyIssue(
                            step_id=step.id,
                            path=path,
                            message=f"Discovery path does not exist in normalized contract schema: {path}",
                        )
                    )
        for raw_path in self.policy.presentation:
            try:
                path = self.semantic.resolve(raw_path, self.paths)
            except UnknownSemanticPath as exc:
                issues.append(DiscoveryPolicyIssue(path=raw_path, message=str(exc)))
                continue
            if not pointer_exists_in_schema(self.raw_schema, path):
                issues.append(DiscoveryPolicyIssue(path=path, message=f"Presentation path not in schema: {path}"))
        return _unique_issues(issues)


def _unique_issues(items: list[DiscoveryPolicyIssue]) -> list[DiscoveryPolicyIssue]:
    seen = set()
    out = []
    for item in items:
        key = (item.step_id, item.path, item.message)
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out
