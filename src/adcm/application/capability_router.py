from adcm.ports.capability import CapabilityHandlerPort


class CapabilityRouter:
    def __init__(self) -> None:
        self._handlers: dict[str, CapabilityHandlerPort] = {}

    def register(self, prefix: str, handler: CapabilityHandlerPort) -> None:
        self._handlers[prefix] = handler

    async def execute(self, capability: str, args: dict) -> dict:
        matches = [(prefix, h) for prefix, h in self._handlers.items() if capability.startswith(prefix)]
        if not matches:
            raise KeyError(f"No capability handler registered for {capability!r}")
        _, handler = max(matches, key=lambda item: len(item[0]))
        return await handler.execute(capability, args)
