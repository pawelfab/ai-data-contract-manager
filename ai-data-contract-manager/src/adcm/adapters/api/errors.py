"""Kontrakt błędów REST API ADCM.

Każdy błąd, niezależnie od statusu, ma ten sam kształt::

    {"error": {"code": "...", "message": "...", "correlation_id": "..."}}

`code` jest stabilnym identyfikatorem do obsługi programowej, `message` tekstem
bezpiecznym do pokazania, a `correlation_id` pozwala powiązać zgłoszenie z
application logiem.

Szczegóły techniczne — treść wyjątku, jego typ, adres Contract Forge, internals MCP —
trafiają wyłącznie do application logu i nigdy do odpowiedzi HTTP.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from adcm.application.observability.app_log_recorder import AppLogRecorder
from adcm.domain.errors import ForgeUnavailableError, SessionNotFoundError

from .models import ErrorBody, ErrorResponse

SESSION_NOT_FOUND = "session_not_found"
CONTRACT_FORGE_UNAVAILABLE = "contract_forge_unavailable"
VALIDATION_ERROR = "validation_error"
INTERNAL_ERROR = "internal_error"

_FORGE_UNAVAILABLE_MESSAGE = "Contract validation service is temporarily unavailable"
_INTERNAL_MESSAGE = "Internal server error"

# Kody dla HTTPException podnoszonych przez sam framework (404 na nieznanej ścieżce,
# 405 na złej metodzie). Nieznany status dostaje kod wyprowadzony ze statusu.
_HTTP_CODES = {
    400: "bad_request",
    404: "not_found",
    405: "method_not_allowed",
    422: VALIDATION_ERROR,
    500: INTERNAL_ERROR,
}

# Deklaracje do OpenAPI — bez nich klient nie wie, jak wygląda odpowiedź błędu.
ERROR_RESPONSES: dict[int | str, dict] = {
    404: {"model": ErrorResponse, "description": "Session not found"},
    422: {"model": ErrorResponse, "description": "Invalid request payload"},
    500: {"model": ErrorResponse, "description": "Internal server error"},
    503: {"model": ErrorResponse, "description": "Contract Forge unavailable"},
}

SESSION_ERROR_RESPONSES: dict[int | str, dict] = {
    404: ERROR_RESPONSES[404],
    500: ERROR_RESPONSES[500],
}


def correlation_id_of(request: Request) -> str | None:
    return getattr(request.state, "correlation_id", None)


def error_response(request: Request, *, status_code: int, code: str, message: str) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorBody(code=code, message=message, correlation_id=correlation_id_of(request))
    )
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


def register_exception_handlers(app: FastAPI, *, app_log: AppLogRecorder) -> None:
    """Rejestruje mapowanie wyjątków na stabilny kontrakt błędu.

    Handlery dla wyjątków domenowych obsługuje `ExceptionMiddleware`, które leży
    wewnątrz middleware aplikacji — dzięki temu odpowiedź wraca zwykłą ścieżką i
    dostaje nagłówek korelacji oraz wpis `http_request_completed`.
    """

    async def _session_not_found(request: Request, exc: SessionNotFoundError) -> JSONResponse:
        return error_response(
            request,
            status_code=404,
            code=SESSION_NOT_FOUND,
            message="Session not found",
        )

    async def _forge_unavailable(request: Request, exc: ForgeUnavailableError) -> JSONResponse:
        app_log.error(
            "contract_forge_unavailable",
            component="http",
            message=str(exc),
            correlation_id=correlation_id_of(request),
            data={"error_type": type(exc).__name__},
        )
        return error_response(
            request,
            status_code=503,
            code=CONTRACT_FORGE_UNAVAILABLE,
            message=_FORGE_UNAVAILABLE_MESSAGE,
        )

    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Wyłącznie lokalizacje pól — wartości z żądania nie wracają do klienta.
        fields = sorted({".".join(str(part) for part in error.get("loc", ())) for error in exc.errors()})
        detail = f": {', '.join(fields)}" if fields else ""
        return error_response(
            request,
            status_code=422,
            code=VALIDATION_ERROR,
            message=f"Request validation failed{detail}",
        )

    async def _http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_CODES.get(exc.status_code, f"http_{exc.status_code}")
        return error_response(
            request,
            status_code=exc.status_code,
            code=code,
            message=str(exc.detail),
        )

    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        app_log.error(
            "unhandled_exception",
            component="http",
            message=str(exc),
            correlation_id=correlation_id_of(request),
            data={"error_type": type(exc).__name__, "path": request.url.path},
        )
        return error_response(
            request,
            status_code=500,
            code=INTERNAL_ERROR,
            message=_INTERNAL_MESSAGE,
        )

    app.add_exception_handler(SessionNotFoundError, _session_not_found)
    app.add_exception_handler(ForgeUnavailableError, _forge_unavailable)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_exception)
    app.add_exception_handler(Exception, _unhandled)
