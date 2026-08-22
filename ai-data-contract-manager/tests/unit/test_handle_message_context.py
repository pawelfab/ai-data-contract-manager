import pytest

from adcm.adapters.outbound.session_memory.repository import MemorySessionRepository
from adcm.application.ports.context_agent import ContextCollectionResult
from adcm.application.ports.forge import ForgeEvaluation, Requirement, SuggestedValue
from adcm.application.ports.llm import Candidate, ResolveResult
from adcm.application.use_cases.create_session import CreateSession
from adcm.application.use_cases.handle_message import HandleMessage
from adcm.application.use_cases.stabilize_contract import StabilizeContract
from adcm.domain.contract.value import Authority
from adcm.domain.evidence.models import EvidenceItem
from adcm.domain.issues.models import AdvisoryIssue


class Forge:
    async def evaluate(self, document, *, user_id=None):
        if "/" and not document.get("source", {}).get("system"):
            return ForgeEvaluation(requirements=[Requirement(path="/source/system", title="Source system")])
        return ForgeEvaluation(
            suggestions=[
                SuggestedValue(
                    path="/silver/dataset",
                    value="aaa_dataset",
                    source="system_enrichment",
                    priority=30,
                )
            ],
            valid=True,
        )


class ContextAgent:
    async def collect(self, request):
        return ContextCollectionResult(
            evidence=[
                EvidenceItem(
                    id="jira-4323",
                    source_type="jira",
                    source_ref="JIRA-4323",
                    authority=Authority.USER_REFERENCED,
                    content="source system is SAP; silver dataset is ddd_dataset",
                )
            ]
        )


class Heuristics:
    async def resolve(self, request):
        for requirement in request.requirements:
            if requirement.path == "/source/system":
                return ResolveResult(
                    candidates=[Candidate(path="/source/system", value="sap", evidence_id="jira-4323")]
                )
        return ResolveResult()

    async def inspect_consistency(self, evidence, current_document):
        return [
            AdvisoryIssue(
                message="Jira says ddd_dataset while existing SAP pipelines use yyy_dataset.",
                paths=["/silver/dataset"],
                requires_user_decision=True,
                evidence_ids=["jira-4323", "schema-pattern"],
            )
        ]

    async def compose_question(self, request):
        return "Potwierdź dataset: Jira wskazuje ddd_dataset, a dotychczasowe pipeline używają yyy_dataset."


@pytest.mark.asyncio
async def test_user_referenced_context_can_fill_forge_requirement_and_conflict_blocks_final_yaml():
    repo = MemorySessionRepository()
    session = await CreateSession(repo).execute()
    heuristics = Heuristics()
    handler = HandleMessage(
        repo,
        StabilizeContract(Forge(), heuristics),
        heuristics,
        ContextAgent(),
    )

    result = await handler.execute(session.id, "Utwórz pipeline SAP na podstawie JIRA-4323")

    assert result.document["source"]["system"] == "sap"
    assert result.document["silver"]["dataset"] == "aaa_dataset"
    assert result.valid is False
    assert result.yaml is None
    assert "Potwierdź dataset" in result.question
    saved = await repo.get(session.id)
    event = saved.contract.latest_user_values()["/source/system"]
    assert event.authority == Authority.USER_REFERENCED
    assert event.provenance.source_ref == "JIRA-4323"
