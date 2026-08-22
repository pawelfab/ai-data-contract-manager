from __future__ import annotations

from collections.abc import Mapping

from contract_forge.domain.enrichment.models import EnrichmentContext, EnrichmentRule, EnrichmentScope


class InMemoryUserEnrichmentRepository:
    """Reference/test adapter showing how per-user enrichment plugs into the port.

    Production can replace this with BigQuery/SQL/Firestore/remote-config without
    changing EvaluateContract or EnrichmentResolver.
    """

    def __init__(self, rules_by_user: Mapping[str, list[EnrichmentRule]] | None = None):
        self.rules_by_user = dict(rules_by_user or {})

    def get_rules(self, context: EnrichmentContext) -> list[EnrichmentRule]:
        if not context.user_id:
            return []
        output: list[EnrichmentRule] = []
        for rule in self.rules_by_user.get(context.user_id, []):
            copy = rule.model_copy(deep=True)
            copy.scope = EnrichmentScope.USER
            copy.user_id = context.user_id
            output.append(copy)
        return output
