from adcm.application.ports.context_agent import AgentContextPort, ContextCollectionRequest, ContextCollectionResult


class NoopContextAgent(AgentContextPort):
    async def collect(self, request: ContextCollectionRequest) -> ContextCollectionResult:
        return ContextCollectionResult()
