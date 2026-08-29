"""Mapowanie modeli core na publiczne DTO API.

Czyste funkcje bez I/O i bez decyzji domenowych: wybierają, co z wyniku tury jest
częścią kontraktu publicznego, i nic poza tym.
"""

from typing import Any

from adcm.domain.forge import ContractStatus, Diagnostic, MissingRequirement
from adcm.domain.mutations import MutationEvent
from adcm.domain.session import SessionState
from adcm.domain.turn import TurnOutcome

from .models import (
    ChangeItem,
    ContractStatusView,
    CreateSessionResponse,
    DiagnosticItem,
    MissingItem,
    SessionStateResponse,
    TurnResponse,
    UnresolvedItem,
)

# Kolejność sprawdzania kluczy `unresolved`. IntentResolution.unresolved jest w core
# typu list[dict[str, Any]] o nieustalonym kształcie — resolver heurystyczny i LLM-owy
# opisują nierozpoznany fragment różnie. Mapper przyjmuje warianty zamiast wymuszać
# zmianę resolvera, która jest poza zakresem tego adaptera.
_INTENT_KEYS = ("intent", "value", "text", "phrase", "message")


def to_contract_status(status: ContractStatus) -> ContractStatusView:
    return ContractStatusView(valid=status.valid, complete=status.complete, clean=status.clean)


def to_missing(item: MissingRequirement) -> MissingItem:
    return MissingItem(path=item.path, code=item.code, message=item.message)


def to_diagnostic(item: Diagnostic) -> DiagnosticItem:
    return DiagnosticItem(
        code=item.code,
        path=item.path,
        severity=item.severity,
        message=item.message,
    )


def to_unresolved(item: dict[str, Any]) -> UnresolvedItem:
    intent = next((str(item[key]) for key in _INTENT_KEYS if item.get(key) is not None), None)
    reason = item.get("reason")
    return UnresolvedItem(intent=intent, reason=str(reason) if reason is not None else None)


def to_change(event: MutationEvent) -> ChangeItem:
    return ChangeItem(
        operation=event.operation.value,
        path=event.path,
        old_value=event.old_value if event.old_exists else None,
        new_value=event.new_value if event.new_exists else None,
    )


def to_turn_response(outcome: TurnOutcome, *, correlation_id: str | None = None) -> TurnResponse:
    return TurnResponse(
        session_id=outcome.session_id,
        turn_no=outcome.turn_no,
        message=outcome.message,
        document=outcome.document,
        contract_status=to_contract_status(outcome.forge.status),
        missing=[to_missing(item) for item in outcome.forge.missing],
        diagnostics=[to_diagnostic(item) for item in outcome.forge.diagnostics],
        unresolved=[to_unresolved(item) for item in outcome.unresolved],
        changes=[to_change(event) for event in outcome.new_events],
        correlation_id=correlation_id,
    )


def to_create_session_response(session: SessionState) -> CreateSessionResponse:
    return CreateSessionResponse(
        session_id=session.session_id,
        turn_no=session.turn_no,
        status="created",
    )


def to_session_state_response(session: SessionState) -> SessionStateResponse:
    """Stan sesji z ostatniego snapshotu.

    Dokument i jego ocena pochodzą z tego samego snapshotu, więc zawsze opisują ten
    sam stan. Sesja bez tur nie ma snapshotu — zwracany jest wtedy pusty dokument
    kontraktu i brak statusu.
    """
    snapshot = session.snapshots[-1] if session.snapshots else None
    if snapshot is None:
        return SessionStateResponse(
            session_id=session.session_id,
            turn_no=session.turn_no,
            document=session.contract.document,
        )
    return SessionStateResponse(
        session_id=session.session_id,
        turn_no=session.turn_no,
        document=snapshot.document,
        contract_status=to_contract_status(snapshot.contract_status),
        missing=[to_missing(item) for item in snapshot.missing],
        diagnostics=[to_diagnostic(item) for item in snapshot.diagnostics],
    )
