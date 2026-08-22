from contract_forge.domain.enrichment.models import EnrichmentContext, EnrichmentRule


class NoopUserEnrichmentRepository:
    """Stage-9 placeholder for the future per-user DB/config adapter."""

    def get_rules(self, context: EnrichmentContext) -> list[EnrichmentRule]:
        return []
