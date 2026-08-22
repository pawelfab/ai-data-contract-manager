from dataclasses import dataclass

from contract_forge.adapters.outbound.contract_file.source import JsonFileContractSource
from contract_forge.adapters.outbound.contract_json_v1.parser import ContractJsonV1Parser
from contract_forge.adapters.outbound.discovery_json.repository import JsonDiscoveryPolicyRepository
from contract_forge.adapters.outbound.enrichment_composite.repository import CompositeEnrichmentRepository
from contract_forge.adapters.outbound.enrichment_json.adapter import JsonEnrichmentRepository
from contract_forge.adapters.outbound.enrichment_user_store.noop import NoopUserEnrichmentRepository
from contract_forge.application.use_cases.evaluate_contract import EvaluateContract

from .settings import Settings


@dataclass
class Container:
    evaluate_contract: EvaluateContract


def build_container(settings: Settings | None = None) -> Container:
    settings = settings or Settings()
    contract_source = JsonFileContractSource(settings.contract_path)
    contract_parser = ContractJsonV1Parser()
    enrichment_repository = CompositeEnrichmentRepository(
        JsonEnrichmentRepository(settings.enrichment_path),
        NoopUserEnrichmentRepository(),
    )
    discovery_repository = JsonDiscoveryPolicyRepository(settings.discovery_path)
    return Container(
        EvaluateContract(
            contract_source=contract_source,
            contract_parser=contract_parser,
            enrichment_repository=enrichment_repository,
            discovery_policy_repository=discovery_repository,
            discovery_strict=settings.discovery_strict,
        )
    )
