import json
from pathlib import Path

from contract_forge.application.definition_normalizer import ContractDefinitionNormalizer
from contract_forge.domain.definition import ContractDefinition


class FileContractDefinitionRepository:
    """Today: file. A future API adapter implements the same port."""

    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.normalizer = ContractDefinitionNormalizer()

    def load(self) -> ContractDefinition:
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return self.normalizer.normalize(raw)
