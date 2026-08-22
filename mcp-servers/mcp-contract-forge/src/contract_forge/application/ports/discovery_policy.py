from typing import Protocol

from contract_forge.domain.discovery.models import DiscoveryPolicy


class DiscoveryPolicyRepositoryPort(Protocol):
    def get_policy(self) -> DiscoveryPolicy: ...
