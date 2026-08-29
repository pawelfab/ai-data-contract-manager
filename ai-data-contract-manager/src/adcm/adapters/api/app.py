"""Adapter HTTP ADCM — jedyny oficjalny interfejs wejściowy usługi.

Adapter odpowiada wyłącznie za::

    HTTP request -> walidacja -> wejście application -> wywołanie application
                 -> mapowanie wyjścia -> HTTP response

Nie zawiera logiki biznesowej: nie modyfikuje `ContractState`, nie interpretuje
wiadomości użytkownika, nie wykonuje reguł, nie woła Contract Forge poza
orchestratorem, nie zna struktury kontraktu i nie podejmuje decyzji o autorytecie
ani o punkcie stałym.

Moduł nie tworzy niczego przy imporcie — kompozycja z konfiguracji środowiska
mieszka w `composition.py`.
"""

from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request

from adcm.application.observability.app_log_recorder import AppLogRecorder
from adcm.application.session_service import SessionService
from adcm.application.turn_orchestrator import TurnOrchestrator
from adcm.domain.session import SessionState

from .errors import ERROR_RESPONSES, SESSION_ERROR_RESPONSES, register_exception_handlers
from .mappers import to_create_session_response, to_session_state_response, to_turn_response
from .models import (
    CreateSessionResponse,
    HealthResponse,
    SessionStateResponse,
    TurnRequest,
    TurnResponse,
)

API_TITLE = "AI Data Contract Manager"
API_VERSION = "0.1.0"
SERVICE_NAME = "adcm"


def create_app(
    *,
    orchestrator: TurnOrchestrator,
    session_service: SessionService,
    app_log: AppLogRecorder,
    debug_api: bool = False,
) -> FastAPI:
    """Buduje aplikację FastAPI na gotowych zależnościach.

    Wszystkie współpracownicy są wstrzykiwani, więc adapter da się uruchomić w teście
    bez środowiska, MCP i dysku.
    """

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        app_log.info("service_started", component="bootstrap")
        yield
        app_log.info("service_stopped", component="bootstrap")

    app = FastAPI(title=API_TITLE, version=API_VERSION, lifespan=lifespan)
    register_exception_handlers(app, app_log=app_log)

    @app.middleware("http")
    async def application_log_middleware(request: Request, call_next):
        correlation_id = uuid4().hex
        request.state.correlation_id = correlation_id
        started = perf_counter()
        app_log.info(
            "http_request_started",
            component="http",
            correlation_id=correlation_id,
            data={"method": request.method, "path": request.url.path},
        )
        try:
            response = await call_next(request)
        except Exception as exc:
            app_log.error(
                "http_request_failed",
                component="http",
                correlation_id=correlation_id,
                duration_ms=(perf_counter() - started) * 1000,
                session_id=_session_id_of(request),
                data={
                    "method": request.method,
                    "route": _route_of(request),
                    "error_type": type(exc).__name__,
                },
            )
            raise
        response.headers["X-Correlation-ID"] = correlation_id
        app_log.info(
            "http_request_completed",
            component="http",
            correlation_id=correlation_id,
            duration_ms=(perf_counter() - started) * 1000,
            session_id=_session_id_of(request),
            data={
                "method": request.method,
                "route": _route_of(request),
                "status_code": response.status_code,
            },
        )
        return response

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        """Liveness usługi. Celowo bez odpytywania Contract Forge."""
        return HealthResponse(status="ok", service=SERVICE_NAME)

    @app.post(
        "/v1/sessions",
        response_model=CreateSessionResponse,
        status_code=201,
        responses={500: ERROR_RESPONSES[500]},
        tags=["sessions"],
    )
    async def create_session() -> CreateSessionResponse:
        session = await session_service.create()
        return to_create_session_response(session)

    @app.get(
        "/v1/sessions/{session_id}",
        response_model=SessionStateResponse,
        responses=SESSION_ERROR_RESPONSES,
        tags=["sessions"],
    )
    async def get_session(session_id: str) -> SessionStateResponse:
        session = await session_service.get(session_id)
        return to_session_state_response(session)

    @app.post(
        "/v1/sessions/{session_id}/turns",
        response_model=TurnResponse,
        responses=ERROR_RESPONSES,
        tags=["turns"],
    )
    @app.post(
        "/v1/sessions/{session_id}/turn",
        response_model=TurnResponse,
        responses=ERROR_RESPONSES,
        deprecated=True,
        tags=["turns"],
    )
    async def submit_turn(session_id: str, request: TurnRequest, http_request: Request) -> TurnResponse:
        await session_service.get(session_id)
        correlation_id = http_request.state.correlation_id
        outcome = await orchestrator.run_turn(
            session_id,
            request.message,
            correlation_id=correlation_id,
        )
        return to_turn_response(outcome, correlation_id=correlation_id)

    if debug_api:

        @app.get(
            "/v1/debug/sessions/{session_id}",
            response_model=SessionState,
            responses=SESSION_ERROR_RESPONSES,
            tags=["debug"],
        )
        async def debug_session(session_id: str) -> SessionState:
            """Pełny stan wewnętrzny sesji. Wyłącznie diagnostyka, poza kontraktem v1."""
            return await session_service.get(session_id)

    return app


def _route_of(request: Request) -> str:
    """Wzorzec ścieżki, nie konkretny URL — inaczej każda sesja jest osobną etykietą."""
    route = request.scope.get("route")
    return getattr(route, "path", None) or request.url.path


def _session_id_of(request: Request) -> str | None:
    return request.scope.get("path_params", {}).get("session_id")
