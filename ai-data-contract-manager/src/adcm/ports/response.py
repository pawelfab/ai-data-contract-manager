from typing import Protocol

from adcm.domain.turn import TurnOutcome


class ResponseComposerPort(Protocol):
    async def compose(self, outcome: TurnOutcome) -> str: ...
