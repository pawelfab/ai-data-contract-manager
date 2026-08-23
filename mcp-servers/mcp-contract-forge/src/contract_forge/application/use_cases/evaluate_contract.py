from __future__ import annotations

from typing import Any

from contract_forge.application.ports.contract_parser import ContractParserPort
from contract_forge.application.ports.contract_source import ContractSourcePort
from contract_forge.application.ports.discovery_policy import DiscoveryPolicyRepositoryPort
from contract_forge.application.ports.enrichment_source import EnrichmentRepositoryPort
from contract_forge.application.services.enrichment_context import EnrichmentContextBuilder
from contract_forge.application.services.enrichment_resolver import resolve_enrichment
from contract_forge.application.services.fillable_requirements import fillable_requirements
from contract_forge.application.services.json_schema_validator import JsonSchemaValidator
from contract_forge.application.services.requirement_discovery import RequirementDiscovery
from contract_forge.application.services.rule_engine import evaluate_rules
from contract_forge.application.services.schema_engine import evaluate_schema
from contract_forge.application.services.schema_paths import enrichment_target_reachable
from contract_forge.application.services.schema_validation_issue_mapper import map_schema_errors
from contract_forge.domain.evaluation.models import ForgeEvaluation, ValidationIssue
from contract_forge.utils.pointer import exists_pointer


class EvaluateContract:
    def __init__(
        self,
        contract_source: ContractSourcePort,
        contract_parser: ContractParserPort,
        enrichment_repository: EnrichmentRepositoryPort,
        discovery_policy_repository: DiscoveryPolicyRepositoryPort,
        *,
        discovery_strict: bool = False,
    ):
        self.contract_source = contract_source
        self.contract_parser = contract_parser
        self.enrichment_repository = enrichment_repository
        self.discovery_policy_repository = discovery_policy_repository
        self.discovery_strict = discovery_strict
        self.schema_validator = JsonSchemaValidator()

    def execute(self, document: dict[str, Any], user_id: str | None = None) -> ForgeEvaluation:
        raw = self.contract_source.load_raw()
        contract = self.contract_parser.parse(raw)

        schema_req, schema_suggestions, issues = evaluate_schema(contract.raw_schema, contract.defs, document)
        rule_req, rule_issues = evaluate_rules(contract.rules, contract.raw_schema, document)
        formal_requirements = _dedup_requirements(schema_req + rule_req)
        issues += rule_issues

        # The Requirement Engine is a discovery tool and may not cover every keyword, so it is
        # never the authority on correctness. `valid` means "this contract is finally correct",
        # not "the conversation can continue" — the conversation is driven by `requirements`,
        # and an in-progress document is legitimately invalid.
        schema_errors = self.schema_validator.validate(contract.raw_schema, document)
        valid = not schema_errors and not [i for i in rule_issues if i.severity == "error"]
        issues += _dedup_issues(map_schema_errors(schema_errors), issues)

        # Enrichment completeness is a property of the contract, not of the conversation: it is
        # built from the full formal set, before the fillable filter and before discovery hides
        # anything. Otherwise "complete" would just mean "nothing is being asked right now".
        open_requirement_paths = {requirement.path for requirement in formal_requirements}

        fillable = fillable_requirements(formal_requirements)
        discovery = RequirementDiscovery(
            self.discovery_policy_repository.get_policy(),
            contract.semantic_paths,
            contract.raw_schema,
            strict=self.discovery_strict,
        ).discover(document=document, requirements=fillable)

        for item in discovery.issues:
            issues.append(
                ValidationIssue(
                    path=item.path,
                    severity="warning",
                    message=item.message,
                    ruleId=f"discovery.{item.step_id}" if item.step_id else "discovery.policy",
                )
            )

        visible_paths = {r.path for r in discovery.requirements}
        # Defaults and enrichment are progressive as well: hidden/later branches are not
        # materialized merely because a rule/default exists.
        suggestions = [s for s in schema_suggestions if s.path in visible_paths or exists_pointer(document, s.path)]

        context = EnrichmentContextBuilder(contract.semantic_paths).build(document, user_id)
        enrichment_rules = self.enrichment_repository.get_rules(context)
        enrichment_paths = set(visible_paths)
        enrichment_paths.update(
            rule.path
            for rule in enrichment_rules
            if rule.path and enrichment_target_reachable(contract.raw_schema, document, rule.path)
        )
        suggestions.extend(
            resolve_enrichment(
                document,
                enrichment_rules,
                context,
                eligible_paths=enrichment_paths,
                open_requirement_paths=open_requirement_paths,
            )
        )
        suggestions = _best_suggestions(suggestions)

        return ForgeEvaluation(
            rulesSpecVersion=contract.rules_spec_version,
            requirements=discovery.requirements,
            suggestions=suggestions,
            issues=issues,
            valid=valid,
        )


def _dedup_issues(candidates, existing):
    """The schema engine already reports const/enum/minItems precisely; keep its wording."""

    taken = {(i.path, i.severity) for i in existing}
    return [i for i in candidates if (i.path, i.severity) not in taken]


def _dedup_requirements(items):
    return list({item.path: item for item in items}.values())


def _best_suggestions(items):
    best = {}
    for item in items:
        if item.path not in best or best[item.path].priority <= item.priority:
            best[item.path] = item
    return list(best.values())
