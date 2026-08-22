import pytest
from adcm.application.ports.forge import ForgeEvaluation, Requirement, SuggestedValue
from adcm.application.ports.llm import ResolveResult, Candidate
from adcm.application.use_cases.stabilize_contract import StabilizeContract
from adcm.domain.contract.value import Authority
from adcm.domain.session.models import Session
from adcm.domain.evidence.models import EvidenceItem


class Forge:
    async def evaluate(self, doc, *, user_id=None):
        if "source" not in doc:
            return ForgeEvaluation(requirements=[Requirement(path="/source/system")])
        return ForgeEvaluation(
            suggestions=[
                SuggestedValue(
                    path="/target/dataset",
                    value="silver_" + doc["source"]["system"],
                    source="system_enrichment",
                    priority=30,
                    sourceRef="ux_rules#systems.sap",
                )
            ],
            valid=True,
        )


class H:
    async def resolve(self, req):
        return ResolveResult(
            candidates=[Candidate(path="/source/system", value="sap", evidence_id="e")]
        )

    async def inspect_consistency(self, evidence, current_document):
        return []

    async def compose_question(self, request):
        return "question"


@pytest.mark.asyncio
async def test_internal_rounds_resolve_then_enrich():
    session = Session(
        evidence=[
            EvidenceItem(
                id="e",
                source_type="jira",
                source_ref="JIRA-4323",
                authority=Authority.USER_REFERENCED,
                content="SAP",
            )
        ]
    )
    result = await StabilizeContract(Forge(), H()).execute(session)
    assert session.contract.effective_document()["target"]["dataset"] == "silver_sap"
    source_event = session.contract.latest_user_values()["/source/system"]
    assert source_event.authority == Authority.USER_REFERENCED
    assert source_event.provenance.source_ref == "JIRA-4323"
    assert result.rounds >= 2


class RepeatForge:
    async def evaluate(self, doc, *, user_id=None):
        if not doc.get("x"):
            return ForgeEvaluation(requirements=[Requirement(path="/x", expectedType="string")])
        return ForgeEvaluation(valid=True)


class RepeatH:
    async def resolve(self, req):
        return ResolveResult(candidates=[Candidate(path="/x", value="same", evidence_id="e")])

    async def inspect_consistency(self, evidence, current_document):
        return []

    async def compose_question(self, request):
        return "question"


@pytest.mark.asyncio
async def test_repeated_same_candidate_reaches_fixed_point():
    session = Session(evidence=[EvidenceItem(id="e", source_type="chat", authority=Authority.USER_DIRECT, content="same")])
    result = await StabilizeContract(RepeatForge(), RepeatH(), max_rounds=5).execute(session)
    assert session.contract.effective_document()["x"] == "same"
    assert result.rounds <= 3


class SwitchingForge:
    async def evaluate(self, doc, *, user_id=None):
        system = doc.get("metadata", {}).get("sourceSystemGcpId")
        suggestions = []
        if system == "sap":
            suggestions = [SuggestedValue(path="/target/dataset", value="silver_sap", source="system_enrichment", priority=20010)]
        elif system == "rocket":
            suggestions = [SuggestedValue(path="/target/dataset", value="silver_rocket", source="system_enrichment", priority=20010)]
        return ForgeEvaluation(suggestions=suggestions, valid=True)


class NoopH:
    async def resolve(self, req):
        return ResolveResult()

    async def inspect_consistency(self, evidence, current_document):
        return []

    async def compose_question(self, request):
        return "question"


@pytest.mark.asyncio
async def test_derived_values_are_recomputed_after_source_system_change():
    session = Session()
    session.contract.set_user("/metadata/sourceSystemGcpId", "sap")
    stabilizer = StabilizeContract(SwitchingForge(), NoopH())
    await stabilizer.execute(session)
    assert session.contract.effective_document()["target"]["dataset"] == "silver_sap"
    session.contract.set_user("/metadata/sourceSystemGcpId", "rocket")
    await stabilizer.execute(session)
    assert session.contract.effective_document()["target"]["dataset"] == "silver_rocket"
