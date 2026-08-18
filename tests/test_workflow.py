from uuid import uuid4
import pytest

from adcm.adapters.llm.rule_based_interpreter import RuleBasedInterpreter
from adcm.adapters.mcp.mock_contract_forge import MockContractForgeAdapter
from adcm.adapters.persistence.memory import InMemorySessionRepository
from adcm.application.chat_service import ChatService
from adcm.application.workflow_runner import WorkflowRunner


@pytest.mark.asyncio
async def test_one_prompt_can_fast_forward_until_only_missing_metadata():
    service = ChatService(
        InMemorySessionRepository(),
        RuleBasedInterpreter(),
        WorkflowRunner(MockContractForgeAdapter()),
    )
    state, result = await service.handle_user_message(
        uuid4(),
        "System unknown-system, CSV ze średnikiem, zawsze UTF-8 i nie używamy szyfrowania.",
    )
    assert result.needs_user_input
    assert result.missing_paths == ["metadata.id"]
    assert state.contract_draft.values["source.system"] == "UNKNOWN-SYSTEM"


@pytest.mark.asyncio
async def test_second_turn_completes_and_user_preference_beats_default():
    sessions = InMemorySessionRepository()
    service = ChatService(sessions, RuleBasedInterpreter(), WorkflowRunner(MockContractForgeAdapter()))
    sid = uuid4()
    await service.handle_user_message(
        sid, "System SAP, CSV ze średnikiem, zawsze UTF-8 i nie używamy szyfrowania."
    )
    state, result = await service.handle_user_message(sid, "id=daily_clients")
    assert result.complete
    assert state.contract_draft.values["source.delimited.delimiter"] == ";"
    assert state.contract_draft.values["source.delimited.encoding"] == "UTF-8"
    assert state.contract_draft.values["preparator.enabled"] is True
    assert state.contract_draft.values["preparator.encryption.enabled"] is False
