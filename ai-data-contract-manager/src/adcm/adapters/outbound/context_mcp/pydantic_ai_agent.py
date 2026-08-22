from uuid import uuid4
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPToolset

from adcm.application.ports.context_agent import (
    AgentContextPort,
    ContextCollectionRequest,
    ContextCollectionResult,
)
from adcm.domain.evidence.models import EvidenceItem


class CollectedEvidence(BaseModel):
    source_type: str
    source_ref: str | None = None
    content: str
    metadata: dict = Field(default_factory=dict)


class ContextAgentOutput(BaseModel):
    evidence: list[CollectedEvidence] = Field(default_factory=list)
    user_visible_output: str | None = None


_INSTRUCTIONS = """
You are ADCM's context/tool agent. Use available MCP tools only when they are relevant to the
user's request. Typical sources are Atlassian/Jira/Wiki, repository/schema exploration and
visualization. Do not call Contract Forge: Forge belongs to ADCM's mandatory deterministic loop.
Return evidence with source_type and a stable source_ref whenever the tool output provides one.
Do not silently choose contract values. Preserve enough source detail for later provenance and
conflict analysis. A visualization may be returned as user_visible_output instead of contract
evidence when appropriate.
""".strip()


class PydanticAiMcpContextAdapter(AgentContextPort):
    def __init__(self, model: str, server_urls: dict[str, str]):
        # MCPToolset supports remote Streamable HTTP URLs. The names remain application
        # configuration, not domain dependencies.
        self.toolsets = [MCPToolset(url) for _, url in sorted(server_urls.items())]
        self.agent = Agent(
            model,
            output_type=ContextAgentOutput,
            instructions=_INSTRUCTIONS,
            toolsets=self.toolsets,
            retries={"tools": 2, "output": 2},
        )

    async def collect(self, request: ContextCollectionRequest) -> ContextCollectionResult:
        prompt = request.model_dump_json(indent=2)
        result = await self.agent.run(prompt)
        evidence = [
            EvidenceItem(
                id=str(uuid4()),
                source_type=item.source_type,
                source_ref=item.source_ref,
                content=item.content,
                authority=request.authority,
                metadata=item.metadata,
            )
            for item in result.output.evidence
        ]
        return ContextCollectionResult(
            evidence=evidence,
            user_visible_output=result.output.user_visible_output,
        )
