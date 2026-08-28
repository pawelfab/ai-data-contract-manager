from typing import Protocol

from adcm.domain.forge import ForgeDescription
from adcm.domain.turn import IntentResolution


class IntentResolverPort(Protocol):
    async def resolve(
        self,
        message: str,
        *,
        document: dict,
        definition: ForgeDescription | None = None,
    ) -> IntentResolution: ...
