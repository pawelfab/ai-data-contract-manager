import os
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from adcm.adapters.forge_mcp import ForgeMcpAdapter
from adcm.adapters.intent_heuristic import HeuristicIntentResolver
from adcm.adapters.response_basic import BasicResponseComposer
from adcm.adapters.rules_file import FileRulesRepository
from adcm.adapters.session_memory import InMemorySessionRepository
from adcm.adapters.logging.bigquery_app_log_sink import BigQueryAppLogSink
from adcm.adapters.logging.bigquery_session_audit_sink import BigQuerySessionAuditSink
from adcm.adapters.logging.local_app_log_sink import LocalAppLogSink
from adcm.adapters.logging.local_session_audit_sink import LocalSessionAuditSink
from adcm.application.candidate_policy import CandidatePolicy
from adcm.application.document_engine import DocumentEngine
from adcm.application.external_check_coordinator import ExternalCheckCoordinator
from adcm.application.proposal_reconciler import ProposalReconciler
from adcm.application.rules_engine import ConventionRulesEngine
from adcm.application.stabilization_engine import StabilizationEngine
from adcm.application.turn_orchestrator import TurnOrchestrator
from adcm.application.observability.app_log_recorder import AppLogRecorder
from adcm.application.observability.session_audit_recorder import SessionAuditRecorder
from adcm.domain.session import SessionState
from adcm.domain.turn import TurnOutcome


class TurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str


def _build_observability() -> tuple[AppLogRecorder, SessionAuditRecorder]:
    backend = os.getenv("ADCM_LOG_BACKEND", "local").lower()
    environment = os.getenv("ADCM_ENVIRONMENT", "local")
    if backend == "local":
        log_dir = os.getenv("ADCM_LOG_DIR", "logs")
        app_sink = LocalAppLogSink(log_dir)
        audit_sink = LocalSessionAuditSink(log_dir)
    elif backend == "bigquery":
        project = os.environ["ADCM_BQ_PROJECT"]
        dataset = os.environ["ADCM_BQ_DATASET"]
        app_sink = BigQueryAppLogSink(
            project,
            dataset,
            os.getenv("ADCM_BQ_APP_LOG_TABLE", "app_logs"),
        )
        audit_sink = BigQuerySessionAuditSink(
            project,
            dataset,
            os.getenv("ADCM_BQ_SESSION_AUDIT_TABLE", "session_audit"),
        )
    else:
        raise RuntimeError(f"Unsupported ADCM_LOG_BACKEND: {backend}")

    app_recorder = AppLogRecorder(app_sink, service="adcm", environment=environment)
    audit_recorder = SessionAuditRecorder(audit_sink, app_recorder)
    app_recorder.info(
        "configuration_loaded",
        component="bootstrap",
        data={"environment": environment, "log_backend": backend},
    )
    return app_recorder, audit_recorder




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

app_log, session_audit = _build_observability()
forge = ForgeMcpAdapter(os.getenv("ADCM_FORGE_URL", "http://localhost:8000/mcp"), app_log=app_log)
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
    audit=session_audit,
    app_log=app_log,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    app_log.info("service_started", component="bootstrap")
    yield
    app_log.info("service_stopped", component="bootstrap")


app = FastAPI(title="AI Data Contract Manager", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def application_log_middleware(request: Request, call_next):
    correlation_id = uuid4().hex
    request.state.correlation_id = correlation_id
    started = perf_counter()
    app_log.info(
        "http_request",
        component="http",
        correlation_id=correlation_id,
        data={"method": request.method, "path": request.url.path},
    )
    try:
        response = await call_next(request)
    except Exception as exc:
        app_log.error(
            "unexpected_exception",
            component="http",
            correlation_id=correlation_id,
            duration_ms=(perf_counter() - started) * 1000,
            data={"method": request.method, "path": request.url.path, "error_type": type(exc).__name__},
        )
        raise
    response.headers["X-Correlation-ID"] = correlation_id
    app_log.info(
        "http_response",
        component="http",
        correlation_id=correlation_id,
        duration_ms=(perf_counter() - started) * 1000,
        data={"method": request.method, "path": request.url.path, "status_code": response.status_code},
    )
    return response


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/sessions/{session_id}/turn", response_model=TurnOutcome)
async def turn(session_id: str, request: TurnRequest, http_request: Request) -> TurnOutcome:
    try:
        return await orchestrator.run_turn(
            session_id,
            request.message,
            correlation_id=http_request.state.correlation_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/v1/sessions/{session_id}", response_model=SessionState)
async def get_session(session_id: str) -> SessionState:
    return await sessions.get_or_create(session_id)
