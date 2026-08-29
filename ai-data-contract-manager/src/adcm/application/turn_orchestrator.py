from time import perf_counter
from uuid import uuid4

from adcm.application.observability.app_log_recorder import AppLogRecorder
from adcm.application.observability.session_audit_recorder import SessionAuditRecorder
from adcm.domain.session import TurnSnapshot
from adcm.domain.turn import TurnOutcome
from adcm.ports.forge import ContractForgePort
from adcm.ports.intent import IntentResolverPort
from adcm.ports.response import ResponseComposerPort
from adcm.ports.rules_repository import RulesRepositoryPort
from adcm.ports.session_repository import SessionRepositoryPort

from .candidate_policy import CandidatePolicy
from .document_engine import DocumentEngine
from .external_check_coordinator import ExternalCheckCoordinator
from .stabilization_engine import StabilizationEngine


class TurnOrchestrator:
    def __init__(
        self,
        *,
        sessions: SessionRepositoryPort,
        forge: ContractForgePort,
        intent: IntentResolverPort,
        rules: RulesRepositoryPort,
        response: ResponseComposerPort,
        candidate_policy: CandidatePolicy,
        document_engine: DocumentEngine,
        stabilization: StabilizationEngine,
        external_checks: ExternalCheckCoordinator,
        audit: SessionAuditRecorder | None = None,
        app_log: AppLogRecorder | None = None,
    ) -> None:
        self.sessions = sessions
        self.forge = forge
        self.intent = intent
        self.rules = rules
        self.response = response
        self.candidate_policy = candidate_policy
        self.document_engine = document_engine
        self.stabilization = stabilization
        self.external_checks = external_checks
        self.audit = audit
        self.app_log = app_log

    async def run_turn(
        self,
        session_id: str,
        user_message: str,
        *,
        correlation_id: str | None = None,
    ) -> TurnOutcome:
        correlation_id = correlation_id or uuid4().hex
        session = await self.sessions.get_or_create(session_id)
        turn_no = session.turn_no + 1
        audit = self.audit.bind(session_id, turn_no, correlation_id) if self.audit is not None else None
        log_start = len(session.contract.mutation_log)
        stage = "turn_start"

        self._audit(
            audit,
            "turn.started",
            {"contract_revision": session.contract.revision},
        )
        self._audit(audit, "user.message.received", {"message": user_message})
        self._app_info(
            "turn_started",
            component="turn_orchestrator",
            correlation_id=correlation_id,
            session_id=session_id,
            turn_no=turn_no,
        )

        try:
            stage = "forge_describe"
            definition = await self.forge.describe(correlation_id=correlation_id)

            stage = "intent_resolution"
            intent_started = perf_counter()
            self._app_info(
                "intent_resolve_started",
                component="intent_resolver",
                correlation_id=correlation_id,
                session_id=session_id,
                turn_no=turn_no,
            )
            resolution = await self.intent.resolve(
                user_message,
                document=session.contract.document,
                definition=definition,
            )
            intent_duration_ms = (perf_counter() - intent_started) * 1000
            self._app_info(
                "intent_resolve_completed",
                component="intent_resolver",
                correlation_id=correlation_id,
                session_id=session_id,
                turn_no=turn_no,
                duration_ms=intent_duration_ms,
                data={"candidate_count": len(resolution.candidates), "unresolved_count": len(resolution.unresolved)},
            )
            self._audit(audit, "intent.resolved", resolution.model_dump(mode="json"))

            stage = "candidate_policy"
            policy_result = self.candidate_policy.evaluate(session.contract, resolution.candidates)
            for decision in policy_result.decisions:
                payload = decision.candidate.model_dump(mode="json")
                payload.update({"reason": decision.reason, "command_id": decision.command_id})
                self._audit(audit, f"candidate.{decision.disposition.value}", payload)
            for unresolved in resolution.unresolved:
                self._audit(audit, "candidate.deferred", unresolved)

            stage = "user_mutations"
            user_events = self.document_engine.apply(session.contract, policy_result.commands)
            for event in user_events:
                self._audit(audit, "mutation.applied", event.model_dump(mode="json"))

            stage = "stabilization"
            effective_rules = await self.rules.load(session_id)
            forge_analysis, stabilization_report = await self.stabilization.stabilize(
                session.contract,
                effective_rules,
                correlation_id=correlation_id,
                audit=audit,
            )
            stage = "external_checks"
            external_status = await self.external_checks.run(document=session.contract.document)
            self._audit(audit, "external_checks.completed", external_status.model_dump(mode="json"))

            session.turn_no = turn_no
            session.snapshots.append(
                TurnSnapshot(
                    turn_no=turn_no,
                    revision=session.contract.revision,
                    document=session.contract.snapshot_document(),
                )
            )
            new_events = session.contract.mutation_log[log_start:]

            provisional = TurnOutcome(
                session_id=session.session_id,
                turn_no=turn_no,
                message="",
                document=session.contract.snapshot_document(),
                forge=forge_analysis,
                external_checks=external_status,
                new_events=new_events,
                stabilization=stabilization_report,
            )
            stage = "response_composition"
            message = await self.response.compose(provisional)
            self._audit(audit, "response.composed", {"message": message})
            outcome = provisional.model_copy(update={"message": message})

            stage = "session_save"
            await self.sessions.save(session)
            self._audit(
                audit,
                "turn.completed",
                {
                    "contract_revision": session.contract.revision,
                    "final_document": outcome.document,
                    "forge_status": outcome.forge.status.model_dump(mode="json"),
                    "missing": [item.model_dump(mode="json") for item in outcome.forge.missing],
                    "diagnostics": [item.model_dump(mode="json") for item in outcome.forge.diagnostics],
                    "external_checks": outcome.external_checks.model_dump(mode="json"),
                    "stabilization": outcome.stabilization.model_dump(mode="json"),
                    "response": outcome.message,
                },
            )
            self._app_info(
                "turn_completed",
                component="turn_orchestrator",
                correlation_id=correlation_id,
                session_id=session_id,
                turn_no=turn_no,
                data={"contract_revision": session.contract.revision},
            )
            return outcome
        except Exception as exc:
            failure = {
                "error_type": type(exc).__name__,
                "component": stage,
                "message": str(exc),
                "contract_revision": session.contract.revision,
            }
            self._audit(audit, "turn.failed", failure)
            if self.app_log is not None:
                self.app_log.error(
                    "turn_failed",
                    component="turn_orchestrator",
                    message=str(exc),
                    correlation_id=correlation_id,
                    session_id=session_id,
                    turn_no=turn_no,
                    data={"stage": stage, "error_type": type(exc).__name__},
                )
            raise

    @staticmethod
    def _audit(audit, event_type: str, data: dict) -> None:
        if audit is not None:
            audit.record(event_type, data)

    def _app_info(self, event: str, **kwargs) -> None:
        if self.app_log is not None:
            self.app_log.info(event, **kwargs)
