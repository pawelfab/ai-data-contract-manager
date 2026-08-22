from contract_forge.application.ports.enrichment_source import EnrichmentRepositoryPort
from contract_forge.domain.enrichment.models import EnrichmentContext, EnrichmentRule


class CompositeEnrichmentRepository:
    """Combines any number of enrichment sources without changing the resolver."""

    def __init__(self, *repositories: EnrichmentRepositoryPort):
        self.repositories = repositories

    def get_rules(self, context: EnrichmentContext) -> list[EnrichmentRule]:
        rules: list[EnrichmentRule] = []
        for repository in self.repositories:
            rules.extend(repository.get_rules(context))
        return rules
