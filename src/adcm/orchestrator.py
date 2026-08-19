from __future__ import annotations

import uuid
from typing import Any

from contract_forge.models import ForgeState, Origin, Requirement
from .gateway import ForgeGateway
from .heuristics import HeuristicResolver
from .models import AssistantTurn, ChatMessage, ConversationMemory
from .semantic import SemanticResolver, NoopSemanticResolver


class ADCMOrchestrator:
    """Thin conversational orchestrator between user/LLM and Contract Forge."""

    def __init__(
        self,
        gateway: ForgeGateway,
        semantic: SemanticResolver | None = None,
        heuristics: HeuristicResolver | None = None,
        max_auto_steps: int = 12,
    ):
        self.gateway = gateway
        self.semantic = semantic or NoopSemanticResolver()
        self.heuristics = heuristics or HeuristicResolver()
        self.max_auto_steps = max_auto_steps
        self.sessions: dict[str, ConversationMemory] = {}

    async def start(self) -> AssistantTurn:
        forge_state = await self.gateway.start_session()
        session_id = str(uuid.uuid4())
        memory = ConversationMemory(session_id=session_id, forge_session_id=forge_state.session_id)
        self.sessions[session_id] = memory
        turn = self._turn_from_state(session_id, forge_state)
        memory.messages.append(ChatMessage(role="assistant", content=turn.message))
        return turn

    async def message(self, session_id: str, text: str) -> AssistantTurn:
        memory = self.sessions[session_id]
        memory.messages.append(ChatMessage(role="user", content=text))
        state = await self.gateway.get_state(memory.forge_session_id)

        # First consume the new message against all currently exposed requirements.
        values: dict[str, Any] = {}
        if state.pending:
            values.update(
                self.heuristics.extract(
                    text,
                    state.pending[:1],
                    state.contract,
                    allow_plain_fallback=True,
                )
            )
            if len(state.pending) > 1:
                values.update(
                    self.heuristics.extract(
                        text,
                        state.pending[1:],
                        state.contract,
                        allow_plain_fallback=False,
                    )
                )
        if values:
            state = await self.gateway.submit_values(memory.forge_session_id, values, Origin.USER)
        else:
            semantic_requirements = self._semantic_prefix(state.pending)
            if semantic_requirements:
                semantic_values = await self.semantic.extract_from_history(
                    session_id, memory.messages, semantic_requirements, state.contract
                )
                if semantic_values:
                    state = await self.gateway.submit_values(memory.forge_session_id, semantic_values, Origin.LLM)

        # Stair-step loop: Forge may reveal requirement B only after A is resolved.
        # Reuse earlier conversation facts without asking the user again.
        for _ in range(self.max_auto_steps):
            if state.status != "needs_input" or not state.pending:
                break

            # Historical deterministic extraction is deliberately strict: no plain-text fallback,
            # otherwise an earlier answer such as "rocket" could become metadata.id later.
            historical_values: dict[str, Any] = {}
            for msg in reversed(memory.messages):
                if msg.role != "user":
                    continue
                found = self.heuristics.extract(
                    msg.content,
                    state.pending,
                    state.contract,
                    allow_plain_fallback=False,
                )
                historical_values.update({k: v for k, v in found.items() if k not in historical_values})
            if historical_values:
                new_state = await self.gateway.submit_values(memory.forge_session_id, historical_values, Origin.USER)
                if new_state.contract != state.contract:
                    state = new_state
                    continue

            semantic_requirements = self._semantic_prefix(state.pending)
            if semantic_requirements:
                semantic_values = await self.semantic.extract_from_history(
                    session_id, memory.messages, semantic_requirements, state.contract
                )
                if semantic_values:
                    new_state = await self.gateway.submit_values(memory.forge_session_id, semantic_values, Origin.LLM)
                    if new_state.contract != state.contract:
                        state = new_state
                        continue
            break

        turn = self._turn_from_state(session_id, state)
        memory.messages.append(ChatMessage(role="assistant", content=turn.message))
        return turn

    async def state(self, session_id: str) -> ForgeState:
        memory = self.sessions[session_id]
        return await self.gateway.get_state(memory.forge_session_id)

    @staticmethod
    def _semantic_prefix(requirements: list[Requirement]) -> list[Requirement]:
        """Return semantic-eligible requirements before the next explicit workflow gate."""
        eligible = []
        for requirement in requirements:
            if requirement.input_mode == "explicit":
                break
            eligible.append(requirement)
        return eligible

    @staticmethod
    def _turn_from_state(session_id: str, state: ForgeState) -> AssistantTurn:
        if state.status == "complete":
            return AssistantTurn(
                session_id=session_id,
                message="Kontrakt jest kompletny i przeszedł walidację Contract Forge.",
                status="complete",
                contract=state.contract,
            )
        if state.status == "invalid":
            details = "; ".join(f"{e.path or '<root>'}: {e.message}" for e in state.validation_errors[:5])
            return AssistantTurn(
                session_id=session_id,
                message=f"Contract Forge zakończył kompletowanie, ale kontrakt jest niepoprawny: {details}",
                status="invalid",
                contract=state.contract,
                validation_errors=[e.model_dump(mode="json") for e in state.validation_errors],
            )
        req = state.pending[0]
        suffix = f" Dostępne: {', '.join(map(str, req.allowed_values))}." if req.allowed_values else ""
        return AssistantTurn(
            session_id=session_id,
            message=req.question + suffix,
            status="needs_input",
            pending_path=req.path,
            contract=state.contract,
        )
