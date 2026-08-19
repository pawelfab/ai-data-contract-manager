from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class AssistantTurn(BaseModel):
    session_id: str
    message: str
    status: Literal["needs_input", "complete", "invalid"]
    pending_path: str | None = None
    contract: dict[str, Any] = Field(default_factory=dict)
    validation_errors: list[dict[str, Any]] = Field(default_factory=list)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ConversationMemory(BaseModel):
    session_id: str
    forge_session_id: str
    messages: list[ChatMessage] = Field(default_factory=list)
