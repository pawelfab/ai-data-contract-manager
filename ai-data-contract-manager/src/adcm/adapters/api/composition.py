"""Composition root ADCM — jedyne miejsce, w którym konfiguracja środowiska staje się obiektami.

Wybór adapterów (Contract Forge, resolver intencji, sinki logów, repozytorium sesji)
odbywa się wyłącznie tutaj. Reszta kodu zna wyłącznie porty.

`build_app()` jest fabryką, nie modułowym globalem — import tego modułu nie czyta
środowiska, nie tworzy plików logów i nie otwiera połączeń::

    uvicorn --factory adcm.adapters.api.composition:build_app
"""

import os

from fastapi import FastAPI

from adcm.adapters.forge_mcp import ForgeMcpAdapter
from adcm.adapters.intent_heuristic import HeuristicIntentResolver
from adcm.adapters.logging.bigquery_app_log_sink import BigQueryAppLogSink
from adcm.adapters.logging.bigquery_session_audit_sink import BigQuerySessionAuditSink
from adcm.adapters.logging.local_app_log_sink import LocalAppLogSink
from adcm.adapters.logging.local_session_audit_sink import LocalSessionAuditSink
from adcm.adapters.response_basic import BasicResponseComposer
from adcm.adapters.rules_file import FileRulesRepository
from adcm.adapters.session_memory import InMemorySessionRepository
from adcm.application.candidate_policy import CandidatePolicy
from adcm.application.document_engine import DocumentEngine
from adcm.application.external_check_coordinator import ExternalCheckCoordinator
from adcm.application.observability.app_log_recorder import AppLogRecorder
from adcm.application.observability.audit_views import AUDIT_LEVEL_NORMAL, AUDIT_LEVELS
from adcm.application.observability.session_audit_recorder import SessionAuditRecorder
from adcm.application.proposal_reconciler import ProposalReconciler
from adcm.application.rules_engine import ConventionRulesEngine
from adcm.application.session_service import SessionService
from adcm.application.stabilization_engine import StabilizationEngine
from adcm.application.turn_orchestrator import TurnOrchestrator

from .app import SERVICE_NAME, create_app


def _build_observability() -> tuple[AppLogRecorder, SessionAuditRecorder]:
    backend = os.getenv("ADCM_LOG_BACKEND", "local").lower()
    environment = os.getenv("ADCM_ENVIRONMENT", "local")
    audit_level = os.getenv("ADCM_AUDIT_LEVEL", AUDIT_LEVEL_NORMAL).lower()
    if audit_level not in AUDIT_LEVELS:
        raise RuntimeError(f"Unsupported ADCM_AUDIT_LEVEL: {audit_level}")
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

    app_recorder = AppLogRecorder(app_sink, service=SERVICE_NAME, environment=environment)
    audit_recorder = SessionAuditRecorder(audit_sink, app_recorder, level=audit_level)
    app_recorder.info(
        "configuration_loaded",
        component="bootstrap",
        data={"environment": environment, "log_backend": backend, "audit_level": audit_level},
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


def _flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def build_app() -> FastAPI:
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
    return create_app(
        orchestrator=orchestrator,
        session_service=SessionService(sessions=sessions),
        app_log=app_log,
        debug_api=_flag("ADCM_DEBUG_API"),
    )
