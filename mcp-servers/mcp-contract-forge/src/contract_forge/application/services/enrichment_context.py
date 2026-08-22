from contract_forge.domain.contract.models import ContractSemanticPaths
from contract_forge.domain.enrichment.models import EnrichmentContext
from contract_forge.utils.pointer import get_pointer


class EnrichmentContextBuilder:
    def __init__(self, paths: ContractSemanticPaths):
        self.paths = paths

    def build(self, document: dict, user_id: str | None) -> EnrichmentContext:
        value = get_pointer(document, self.paths.source_system, None)
        return EnrichmentContext(
            user_id=user_id,
            source_system=None if value is None else str(value),
        )
