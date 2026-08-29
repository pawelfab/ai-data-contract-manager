from typing import Any

from adcm.application.observability.app_log_recorder import AppLogRecorder
from adcm.application.observability.audit_views import AUDIT_LEVEL_NORMAL, AUDIT_LEVELS
from adcm.application.observability.models import SessionAuditEvent
from adcm.ports.session_audit_sink import SessionAuditSinkPort


class BoundTurnAuditRecorder:
    def __init__(self, parent: "SessionAuditRecorder", session_id: str, turn_no: int, correlation_id: str | None):
        self.parent, self.session_id, self.turn_no, self.correlation_id = parent, session_id, turn_no, correlation_id

    @property
    def level(self) -> str:
        """Audit verbosity, used by callers to pick a compact or a full payload."""
        return self.parent.level

    def emit(self, event_type: str, data: Any = None, **kwargs: Any) -> SessionAuditEvent:
        payload = _dump(data) if data is not None else {}
        payload.update({k: _dump(v) for k, v in kwargs.items()})
        return self.parent._emit(self.session_id, self.turn_no, self.correlation_id, event_type, payload)

    def record(self, event_type: str, data: Any = None, **kwargs: Any) -> SessionAuditEvent:
        """Record an event using the stable primitive shared by integrations."""
        return self.emit(event_type, data, **kwargs)

    def __getattr__(self, name: str):
        event_type = _EVENT_NAMES.get(name)
        if event_type is None:
            raise AttributeError(name)
        return lambda data=None, **kwargs: self.emit(event_type, data, **kwargs)


class SessionAuditRecorder:
    def __init__(self, sink: SessionAuditSinkPort, app_log: AppLogRecorder, *, level: str = AUDIT_LEVEL_NORMAL):
        if level not in AUDIT_LEVELS:
            raise ValueError(f"Unsupported audit level: {level}")
        self.sink, self.app_log, self.level = sink, app_log, level

    def bind(self, session_id: str, turn_no: int, correlation_id: str | None = None) -> BoundTurnAuditRecorder:
        return BoundTurnAuditRecorder(self, session_id, turn_no, correlation_id)

    def _emit(self, session_id: str, turn_no: int, correlation_id: str | None, event_type: str, data: dict[str, Any]):
        event = SessionAuditEvent(session_id=session_id, turn_no=turn_no, correlation_id=correlation_id,
                                  event_type=event_type, data=data)
        try:
            self.sink.emit(event)
        except Exception as exc:
            self.app_log.error("session_audit_sink_failed", component="session_audit",
                               correlation_id=correlation_id, session_id=session_id, turn_no=turn_no,
                               data={"failed_event_type": event_type,
                                     "failed_event_count": getattr(exc, "failed_event_count", 1)})
        return event


def _dump(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(k): _dump(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_dump(v) for v in value]
    return value


_EVENT_NAMES = {
    "turn_started": "turn.started", "user_message_received": "user.message.received", "intent_resolved": "intent.resolved",
    "candidate_accepted": "candidate.accepted", "candidate_rejected": "candidate.rejected", "candidate_deferred": "candidate.deferred",
    "mutation_applied": "mutation.applied", "forge_analysis_started": "forge.analysis.started", "forge_analysis_completed": "forge.analysis.completed",
    "rule_proposal_generated": "rule.proposal.generated", "forge_proposal_received": "forge.proposal.received", "proposal_decision": "proposal.decision",
    "stabilization_round_started": "stabilization.round.started", "stabilization_round_completed": "stabilization.round.completed", "stabilization_completed": "stabilization.completed",
    "external_checks_completed": "external_checks.completed", "response_composed": "response.composed", "turn_completed": "turn.completed", "turn_failed": "turn.failed",
    "forge_started": "forge.analysis.started", "forge_completed": "forge.analysis.completed",
    "rule_proposal": "rule.proposal.generated", "external_checks": "external_checks.completed",
}

# Compatibility alias for the initial implementation name.
BoundTurnAuditBuffer = BoundTurnAuditRecorder
