from typing import Protocol

from adcm.domain.forge import ForgeAnalysis, ForgeDescription


class ContractForgePort(Protocol):
    async def analyze(self, document: dict, *, correlation_id: str | None = None) -> ForgeAnalysis: ...
    async def describe(self, *, correlation_id: str | None = None) -> ForgeDescription: ...
