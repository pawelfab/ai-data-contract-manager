from pathlib import Path

from contract_forge.adapters.outbound.contract_file.source import JsonFileContractSource
from contract_forge.domain.contract.models import NormalizedContract

from .parser import ContractJsonV1Parser


class ContractJsonV1Adapter:
    """Compatibility facade. New wiring uses source + parser as separate ports."""

    def __init__(self, path: str | Path):
        self.source = JsonFileContractSource(path)
        self.parser = ContractJsonV1Parser()

    def load(self) -> NormalizedContract:
        return self.parser.parse(self.source.load_raw())
