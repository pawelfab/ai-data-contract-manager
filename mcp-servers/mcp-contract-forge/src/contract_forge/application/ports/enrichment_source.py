from typing import Protocol

from contract_forge.domain.enrichment.models import EnrichmentContext, EnrichmentRule


class EnrichmentRepositoryPort(Protocol):
    """Returns declarative enrichment rules relevant to an evaluation context."""

    def get_rules(self, context: EnrichmentContext) -> list[EnrichmentRule]: ...
