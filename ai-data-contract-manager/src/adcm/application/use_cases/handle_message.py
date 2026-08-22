from uuid import uuid4
from pydantic import BaseModel, Field
from adcm.application.ports.context_agent import AgentContextPort, ContextCollectionRequest
from adcm.application.ports.llm import HeuristicsPort, QuestionRequest
from adcm.application.ports.session_repository import SessionRepositoryPort
from adcm.application.use_cases.stabilize_contract import StabilizeContract
from adcm.domain.contract.value import Authority
from adcm.domain.evidence.models import EvidenceItem, Message
from adcm.domain.issues.models import AdvisoryIssue
from adcm.rendering.yaml_renderer import render_yaml


class HandleResult(BaseModel):
    session_id: str
    valid: bool
    question: str | None = None
    yaml: str | None = None
    warnings: list[AdvisoryIssue] = Field(default_factory=list)
    document: dict = Field(default_factory=dict)
    tool_output: str | None = None


class HandleMessage:
    def __init__(
        self,
        repo: SessionRepositoryPort,
        stabilizer: StabilizeContract,
        heuristics: HeuristicsPort,
        context_agent: AgentContextPort,
    ):
        self.repo = repo
        self.stabilizer = stabilizer
        self.heuristics = heuristics
        self.context_agent = context_agent

    async def execute(
        self,
        session_id: str,
        content: str,
        attachment_texts: list[str] | None = None,
    ) -> HandleResult:
        session = await self.repo.get(session_id)
        if not session:
            raise KeyError(session_id)

        session.messages.append(Message(role="user", content=content))
        session.evidence.append(
            EvidenceItem(
                id=str(uuid4()),
                source_type="chat",
                content=content,
                authority=Authority.USER_DIRECT,
            )
        )
        for text in attachment_texts or []:
            session.evidence.append(
                EvidenceItem(
                    id=str(uuid4()),
                    source_type="attachment_text",
                    content=text,
                    authority=Authority.USER_DIRECT,
                )
            )

        # Agentic/context MCPs may collect Jira/Wiki/repository/schema evidence or create
        # user-visible tool output. Contract Forge is intentionally not available here.
        context_result = await self.context_agent.collect(
            ContextCollectionRequest(
                user_request=content,
                history=session.messages,
                current_document=session.contract.effective_document(),
                authority=Authority.USER_REFERENCED,
            )
        )
        session.evidence.extend(context_result.evidence)

        result = await self.stabilizer.execute(session)
        await self.repo.save(session)

        document = session.contract.effective_document()
        unresolved = [r for r in result.evaluation.requirements if _missing(document, r.path)]
        decision_warnings = [w for w in result.warnings if w.requires_user_decision]

        question = None
        if unresolved or decision_warnings:
            question = await self.heuristics.compose_question(
                QuestionRequest(
                    requirements=unresolved,
                    warnings=result.warnings,
                    history=session.messages,
                    current_document=document,
                )
            )

        ready = result.evaluation.valid and not unresolved and not decision_warnings
        return HandleResult(
            session_id=session.id,
            valid=ready,
            question=question,
            yaml=render_yaml(document) if ready else None,
            warnings=result.warnings,
            document=document,
            tool_output=context_result.user_visible_output,
        )


def _missing(document, pointer):
    from adcm.domain.contract.path import get_pointer

    return get_pointer(document, pointer, None) is None
