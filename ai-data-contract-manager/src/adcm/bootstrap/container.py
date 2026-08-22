from dataclasses import dataclass
from adcm.adapters.outbound.session_memory.repository import MemorySessionRepository
from adcm.adapters.outbound.forge_mcp.client import ForgeMcpAdapter
from adcm.adapters.outbound.llm.heuristics import ConservativeLocalHeuristics
from adcm.application.use_cases.create_session import CreateSession
from adcm.application.use_cases.stabilize_contract import StabilizeContract
from adcm.application.use_cases.handle_message import HandleMessage
from .settings import Settings


@dataclass
class Container:
    repo: MemorySessionRepository
    create_session: CreateSession
    handle_message: HandleMessage


def build_container(settings: Settings | None = None) -> Container:
    settings = settings or Settings()
    repo = MemorySessionRepository()
    forge = ForgeMcpAdapter(settings.forge_mcp_url)

    if settings.llm_mode == "pydantic-ai":
        from adcm.adapters.outbound.llm.pydantic_ai_heuristics import PydanticAiHeuristicsAdapter

        heuristics = PydanticAiHeuristicsAdapter(
            settings.llm_model,
            base_url=settings.llm_base_url,
            api_key=settings.openai_api_key,
        )
    else:
        heuristics = ConservativeLocalHeuristics()

    if settings.context_mcp_urls and settings.llm_mode == "pydantic-ai":
        from adcm.adapters.outbound.context_mcp.pydantic_ai_agent import PydanticAiMcpContextAdapter

        context_agent = PydanticAiMcpContextAdapter(settings.llm_model, settings.context_mcp_urls)
    else:
        from adcm.adapters.outbound.context_mcp.noop import NoopContextAgent

        context_agent = NoopContextAgent()

    stabilizer = StabilizeContract(forge, heuristics, settings.max_stabilization_rounds)
    return Container(
        repo=repo,
        create_session=CreateSession(repo),
        handle_message=HandleMessage(repo, stabilizer, heuristics, context_agent),
    )
