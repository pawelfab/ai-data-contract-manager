from typing import Any, Protocol

from contract_forge.domain.contract.models import NormalizedContract


class ContractParserPort(Protocol):
    """Maps one concrete source format to Forge's stable normalized domain model."""

    def parse(self, raw: dict[str, Any]) -> NormalizedContract: ...
