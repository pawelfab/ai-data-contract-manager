from typing import Protocol
from adcm.domain.models import AgentContext, TurnInterpretation


class SemanticInterpreterPort(Protocol):
    async def interpret_turn(self, text: str, context: AgentContext) -> TurnInterpretation: ...
