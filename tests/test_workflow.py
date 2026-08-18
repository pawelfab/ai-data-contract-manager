from uuid import uuid4

import pytest

from adcm.adapters.mcp.mock_contract_forge import MockContractForgeAdapter
from adcm.adapters.persistence.memory import InMemorySessionRepository
from adcm.application.chat_service import ChatService
from adcm.application.workflow_runner import WorkflowRunner
from adcm.domain.models import (
    AgentContext,
    ExtractedPreference,
    ExtractedSignal,
    TurnInterpretation,
    WorkflowOutcomeStatus,
)


class QueueInterpreter:
    def __init__(self, results):
        self.results = list(results)

    async def interpret_turn(self, text: str, context: AgentContext) -> TurnInterpretation:
        return self.results.pop(0)


@pytest.mark.asyncio
async def test_fast_forward_until_metadata_id_required():
    interpreter = QueueInterpreter(
        [
            TurnInterpretation(
                extracted_signals=[
                    ExtractedSignal(concept="source_system", value="SAP"),
                    ExtractedSignal(concept="source_format", value="csv"),
                    ExtractedSignal(concept="field_delimiter", value=";"),
                ],
                preferences=[
                    ExtractedPreference(concept="encoding", value="UTF-8"),
                    ExtractedPreference(concept="encryption", value=False),
                ],
            )
        ]
    )
    service = ChatService(
        InMemorySessionRepository(), interpreter, WorkflowRunner(MockContractForgeAdapter())
    )
    state, outcome = await service.handle_user_message(uuid4(), "test input")
    assert outcome.status == WorkflowOutcomeStatus.WAITING_FOR_USER
    assert outcome.missing_paths == ["metadata.id"]
    assert [r.path for r in state.workflow.pending_requirements] == ["metadata.id"]
    assert state.contract_draft.values["source"]["system"] == "SAP"
    assert state.contract_draft.values["source"]["delimited"]["delimiter"] == ";"
    assert state.contract_draft.values["preparator"]["enabled"] is True


@pytest.mark.asyncio
async def test_second_turn_completes_and_user_preference_beats_default():
    sessions = InMemorySessionRepository()
    interpreter = QueueInterpreter(
        [
            TurnInterpretation(
                extracted_signals=[
                    ExtractedSignal(concept="source_system", value="SAP"),
                    ExtractedSignal(concept="source_format", value="csv"),
                    ExtractedSignal(concept="field_delimiter", value=";"),
                ],
                preferences=[
                    ExtractedPreference(concept="encoding", value="UTF-8"),
                    ExtractedPreference(concept="encryption", value=False),
                ],
            ),
            TurnInterpretation(
                extracted_signals=[ExtractedSignal(concept="feed_name", value="daily_clients")]
            ),
        ]
    )
    service = ChatService(sessions, interpreter, WorkflowRunner(MockContractForgeAdapter()))
    sid = uuid4()
    await service.handle_user_message(sid, "first")
    state, outcome = await service.handle_user_message(sid, "second")
    assert outcome.status == WorkflowOutcomeStatus.COMPLETE
    assert state.contract_draft.values["metadata"]["id"] == "daily_clients"
    assert state.contract_draft.values["source"]["delimited"]["encoding"] == "UTF-8"
    assert state.contract_draft.values["preparator"]["encryption"]["enabled"] is False
