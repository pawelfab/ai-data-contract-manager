from __future__ import annotations

from typing import Any

from contract_forge.application.ports.contract_parser import ContractParserPort
from contract_forge.application.ports.contract_source import ContractSourcePort
from contract_forge.application.ports.discovery_policy import DiscoveryPolicyRepositoryPort
from contract_forge.application.ports.enrichment_source import EnrichmentRepositoryPort
from contract_forge.application.services.enrichment_context import EnrichmentContextBuilder
from contract_forge.application.services.enrichment_resolver import resolve_enrichment
from contract_forge.application.services.fillable_requirements import fillable_requirements
from contract_forge.application.services.requirement_discovery import RequirementDiscovery
from contract_forge.application.services.rule_engine import evaluate_rules
from contract_forge.application.services.schema_engine import evaluate_schema
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

    def execute(self, document: dict[str, Any], user_id: str | None = None) -> ForgeEvaluation:
        raw = self.contract_source.load_raw()
        contract = self.contract_parser.parse(raw)

        schema_req, schema_suggestions, issues = evaluate_schema(contract.raw_schema, contract.defs, document)
        rule_req, rule_issues = evaluate_rules(contract.rules, contract.raw_schema, document)
        formal_requirements = _dedup_requirements(schema_req + rule_req)
        issues += rule_issues

        # Final validity is intentionally independent from UX discovery/filtering.
        unresolved_formal = [r for r in formal_requirements if not exists_pointer(document, r.path)]
        valid = not unresolved_formal and not [i for i in issues if i.severity == "error"]

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
        suggestions.extend(
            resolve_enrichment(
                document,
                enrichment_rules,
                context,
                eligible_paths=visible_paths,
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


def _dedup_requirements(items):
    return list({item.path: item for item in items}.values())


def _best_suggestions(items):
    best = {}
    for item in items:
        if item.path not in best or best[item.path].priority <= item.priority:
            best[item.path] = item
    return list(best.values())
