from __future__ import annotations

from threading import RLock
from typing import Any

from .models import ContractState


class SessionStore:
    """Small in-memory store for the MVP, keyed by Pydantic AI conversation_id."""

    def __init__(self) -> None:
        self._states: dict[str, ContractState] = {}
        self._lock = RLock()

    def get(self, conversation_id: str) -> ContractState:
        with self._lock:
            state = self._states.get(conversation_id)
            if state is None:
                state = ContractState(conversation_id=conversation_id)
                self._states[conversation_id] = state
            return state.model_copy(deep=True)

    def save(self, state: ContractState) -> None:
        with self._lock:
            self._states[state.conversation_id] = state.model_copy(deep=True)

    def capture_history(
        self, conversation_id: str, history: list[dict[str, Any]]
    ) -> ContractState:
        state = self.get(conversation_id)
        state.chat_history = history
        self.save(state)
        return state
