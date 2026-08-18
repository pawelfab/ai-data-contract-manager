import asyncio
from uuid import uuid4

from adcm.adapters.llm.rule_based_interpreter import RuleBasedInterpreter
from adcm.adapters.mcp.mock_contract_forge import MockContractForgeAdapter
from adcm.adapters.persistence.memory import InMemorySessionRepository
from adcm.application.chat_service import ChatService
from adcm.application.workflow_runner import WorkflowRunner


async def main() -> None:
    sessions = InMemorySessionRepository()
    service = ChatService(
        sessions=sessions,
        interpreter=RuleBasedInterpreter(),
        workflow=WorkflowRunner(MockContractForgeAdapter()),
    )
    session_id = uuid4()

    turns = [
        "System SAP, CSV ze średnikiem, zawsze UTF-8 i nie używamy szyfrowania.",
        "id=daily_clients",
    ]
    for text in turns:
        state, result = await service.handle_user_message(session_id, text)
        print("USER:", text)
        print("stage:", state.workflow.current_stage)
        print("needs_user_input:", result.needs_user_input, result.missing_paths)
        print("draft:", state.contract_draft.model_dump())
        print()


if __name__ == "__main__":
    asyncio.run(main())
