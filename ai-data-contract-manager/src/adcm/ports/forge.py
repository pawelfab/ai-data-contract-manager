from typing import Protocol

from adcm.domain.forge import ForgeAnalysis, ForgeDescription


class ContractForgePort(Protocol):
    async def analyze(self, document: dict) -> ForgeAnalysis: ...
    async def describe(self) -> ForgeDescription: ...
