from typing import Protocol

from contract_forge.domain.definition import ContractDefinition


class ContractDefinitionPort(Protocol):
    def load(self) -> ContractDefinition: ...
