from typing import Any, Protocol


class CapabilityHandlerPort(Protocol):
    async def execute(self, capability: str, args: dict[str, Any]) -> dict[str, Any]: ...
