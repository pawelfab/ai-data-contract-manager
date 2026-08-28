import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict

from adcm.adapters.forge_mcp import ForgeMcpAdapter
from adcm.adapters.intent_heuristic import HeuristicIntentResolver
from adcm.adapters.response_basic import BasicResponseComposer
from adcm.adapters.rules_file import FileRulesRepository
from adcm.adapters.session_memory import InMemorySessionRepository
from adcm.application.candidate_policy import CandidatePolicy
from adcm.application.document_engine import DocumentEngine
from adcm.application.external_check_coordinator import ExternalCheckCoordinator
from adcm.application.proposal_reconciler import ProposalReconciler
from adcm.application.rules_engine import ConventionRulesEngine
from adcm.application.stabilization_engine import StabilizationEngine
from adcm.application.turn_orchestrator import TurnOrchestrator
from adcm.domain.session import SessionState
from adcm.domain.turn import TurnOutcome


class TurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str




def _build_intent_resolver():
    mode = os.getenv("ADCM_INTENT_MODE", "heuristic").lower()
    if mode == "heuristic":
        return HeuristicIntentResolver()
    if mode == "pydantic-ai":
        try:
            from adcm.adapters.intent_pydantic_ai import PydanticAIIntentResolver
        except ImportError as exc:  # optional dependency
            raise RuntimeError("ADCM_INTENT_MODE=pydantic-ai requires requirements-ai.txt") from exc
        model = os.getenv("ADCM_MODEL")
        if not model:
            raise RuntimeError("ADCM_MODEL is required when ADCM_INTENT_MODE=pydantic-ai")
        return PydanticAIIntentResolver(model)
    raise RuntimeError(f"Unsupported ADCM_INTENT_MODE: {mode}")

forge = ForgeMcpAdapter(os.getenv("ADCM_FORGE_URL", "http://localhost:8000/mcp"))
document_engine = DocumentEngine()
stabilization = StabilizationEngine(
    forge=forge,
    document_engine=document_engine,
    rules_engine=ConventionRulesEngine(),
    proposal_reconciler=ProposalReconciler(),
    max_rounds=int(os.getenv("ADCM_MAX_STABILIZATION_ROUNDS", "8")),
)
sessions = InMemorySessionRepository()
orchestrator = TurnOrchestrator(
    sessions=sessions,
    forge=forge,
    intent=_build_intent_resolver(),
    rules=FileRulesRepository(os.getenv("ADCM_RULES_PATH", "/app/resources/ux_rules.json")),
    response=BasicResponseComposer(),
    candidate_policy=CandidatePolicy(),
    document_engine=document_engine,
    stabilization=stabilization,
    external_checks=ExternalCheckCoordinator(),
)

app = FastAPI(title="AI Data Contract Manager", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/sessions/{session_id}/turn", response_model=TurnOutcome)
async def turn(session_id: str, request: TurnRequest) -> TurnOutcome:
    try:
        return await orchestrator.run_turn(session_id, request.message)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/v1/sessions/{session_id}", response_model=SessionState)
async def get_session(session_id: str) -> SessionState:
    return await sessions.get_or_create(session_id)
