from uuid import UUID

from adcm.application.context_builder import AgentContextBuilder
from adcm.application.turn_processor import TurnProcessor
from adcm.application.workflow_runner import WorkflowRunner, WorkflowResult
from adcm.domain.models import ChatMessage, ConversationState
from adcm.ports.semantic_interpreter import SemanticInterpreterPort
from adcm.ports.session_repository import SessionRepositoryPort


class ChatService:
    def __init__(
        self,
        sessions: SessionRepositoryPort,
        interpreter: SemanticInterpreterPort,
        workflow: WorkflowRunner,
    ) -> None:
        self.sessions = sessions
        self.interpreter = interpreter
        self.workflow = workflow
        self.context_builder = AgentContextBuilder()
        self.turn_processor = TurnProcessor()

    async def handle_user_message(
        self,
        session_id: UUID,
        text: str,
    ) -> tuple[ConversationState, WorkflowResult]:
        state = await self.sessions.load(session_id) or ConversationState(session_id=session_id)
        message = ChatMessage(role="user", content=text)
        context = self.context_builder.build(state)
        interpretation = await self.interpreter.interpret_turn(text, context)
        self.turn_processor.apply_user_turn(state, message, interpretation)
        result = await self.workflow.run(state)
        await self.sessions.save(state)
        return state, result
