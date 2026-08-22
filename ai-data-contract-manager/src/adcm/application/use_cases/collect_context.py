from adcm.application.ports.context_provider import ContextProviderPort, ContextRequest
from adcm.domain.session.models import Session

class CollectContext:
    def __init__(self, providers: list[ContextProviderPort]): self.providers=providers
    async def execute(self, session: Session, request: ContextRequest) -> int:
        count=0
        for provider in self.providers:
            items=await provider.collect(request); session.evidence.extend(items); count += len(items)
        return count
