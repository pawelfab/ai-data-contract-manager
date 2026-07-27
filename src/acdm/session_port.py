from __future__ import annotations

from typing import Protocol

from .models import ContractState


class SessionStatePort(Protocol):
    """Storage-independent access to deterministic conversation state."""

    async def get(self, conversation_id: str) -> ContractState: ...

    async def save(self, state: ContractState) -> None: ...
