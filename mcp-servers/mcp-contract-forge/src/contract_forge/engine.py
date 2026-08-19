from __future__ import annotations

import json
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .models import ForgeState, Origin, Requirement, RuleIssue, SessionData, ValidationIssue
from .path_utils import has_path, write_value
from .rules import RuleEngine
from .schema import SchemaNavigator


class ContractForge:
    """Canonical owner of contract construction state.

    ADCM never directly mutates the canonical contract. It submits candidate values and
    receives the next set of requirements. Enrichment/default precedence is:

      user > system enrichment > generic enrichment > schema default.

    Deterministic and LLM extraction are ADCM concerns; both submit USER facts.
    """

    def __init__(self, schema: dict[str, Any], rules: dict[str, Any], deploy_env: str = "dev"):
        Draft202012Validator.check_schema(schema)
        self.navigator = SchemaNavigator(schema)
        self.rule_engine = RuleEngine(rules, self.navigator, deploy_env=deploy_env)
        self.sessions: dict[str, SessionData] = {}

    @classmethod
    def from_files(cls, schema_path: str | Path, rules_path: str | Path, deploy_env: str = "dev") -> "ContractForge":
        schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
        rules = json.loads(Path(rules_path).read_text(encoding="utf-8"))
        return cls(schema, rules, deploy_env=deploy_env)

    def list_source_systems(self) -> list[dict[str, Any]]:
        return [
            {"id": system, "source_types": self.rule_engine.source_types(system)}
            for system in self.rule_engine.systems
        ]

    def start_session(self) -> ForgeState:
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = SessionData(session_id=session_id)
        return self._state(self.sessions[session_id])

    def submit_values(self, session_id: str, values: dict[str, Any], origin: Origin = Origin.USER) -> ForgeState:
        session = self._get(session_id)
        allowed = {r.path for r in self._pending(session)}
        session.candidate_issues.clear()
        # The source-system gate is always permitted until selected.
        if session.source_system is None:
            allowed.add("metadata.sourceSystemGcpId")

        for path, value in values.items():
            if not self._candidate_path_allowed(session, path, origin, allowed):
                session.candidate_issues.append(self._disallowed_path_issue(session, path))
                continue
            session.candidate_issues.extend(self._apply_explicit(session, path, value, origin))

        self._advance(session)
        return self._state(session)

    def get_state(self, session_id: str) -> ForgeState:
        session = self._get(session_id)
        self._advance(session)
        return self._state(session)

    def _candidate_path_allowed(
        self,
        session: SessionData,
        path: str,
        origin: Origin,
        pending: set[str],
    ) -> bool:
        if path in pending:
            return True
        if origin != Origin.USER or not has_path(session.contract, path):
            return False
        if not self.navigator.path_exists_in_schema(path, session.contract):
            return False
        return session.origins.get(path) in {
            Origin.USER,
            Origin.SYSTEM_ENRICHMENT,
            Origin.GENERIC_ENRICHMENT,
            Origin.SCHEMA_DEFAULT,
        }

    def _disallowed_path_issue(self, session: SessionData, path: str) -> ValidationIssue:
        if not self.navigator.path_exists_in_schema(path, session.contract):
            return ValidationIssue(
                path=path,
                message="Candidate path does not exist in the active contract schema.",
                validator="path",
            )
        return ValidationIssue(
            path=path,
            message="Candidate path is neither pending nor an overridable existing value.",
            validator="candidate_path",
        )

    def _apply_explicit(
        self,
        session: SessionData,
        path: str,
        value: Any,
        origin: Origin,
    ) -> list[ValidationIssue]:
        if path == "metadata.sourceSystemGcpId":
            canonical = str(value).strip().lower()
            if canonical not in self.rule_engine.systems:
                return [ValidationIssue(path=path, message="Unknown source system.", validator="enum")]
            applied = write_value(session.contract, session.origins, path, canonical.upper(), origin)
            if not applied:
                return [ValidationIssue(path=path, message="Candidate lost origin precedence.", validator="precedence")]
            session.source_system = canonical
            session.applied.append(applied)
            return []

        if path == "source.sourceType":
            candidate = str(value).strip().lower()
            if candidate not in self._source_type_choices(session):
                return [ValidationIssue(path=path, message="Unsupported source type.", validator="enum")]
            applied = write_value(session.contract, session.origins, path, candidate, origin)
            if not applied:
                return [ValidationIssue(path=path, message="Candidate lost origin precedence.", validator="precedence")]
            session.applied.append(applied)
            return []

        node = self.navigator.schema_at_path(path, session.contract)
        if node is None:
            return [ValidationIssue(path=path, message="Candidate path does not exist in the active contract schema.", validator="path")]
        # Validate the candidate against its local schema before accepting it.
        local_errors = self.navigator.validate_value(node, value)
        if local_errors:
            return [
                issue.model_copy(update={"path": f"{path}.{issue.path}" if issue.path else path})
                for issue in local_errors
            ]
        applied = write_value(session.contract, session.origins, path, deepcopy(value), origin)
        if not applied:
            return [ValidationIssue(path=path, message="Candidate lost origin precedence.", validator="precedence")]
        session.applied.append(applied)
        return []

    def _advance(self, session: SessionData) -> None:
        if session.source_system is None:
            return

        # Required objects are structural, not user decisions.
        self.navigator.ensure_required_containers(session.contract, session.origins)

        # Run to a fixpoint because later rules can become eligible after earlier rules/defaults.
        for _ in range(8):
            before = json.dumps(session.contract, sort_keys=True, default=str)
            session.applied.extend(self.rule_engine.apply_system_source_type(session.contract, session.origins, session.source_system))

            applied, _ = self.rule_engine.apply_pass(
                session.contract, session.origins, session.source_system, Origin.SYSTEM_ENRICHMENT
            )
            session.applied.extend(applied)

            applied, _ = self.rule_engine.apply_pass(
                session.contract, session.origins, session.source_system, Origin.GENERIC_ENRICHMENT
            )
            session.applied.extend(applied)

            session.applied.extend(self.navigator.inject_defaults(session.contract, session.origins))

            self.navigator.ensure_required_containers(session.contract, session.origins)
            after = json.dumps(session.contract, sort_keys=True, default=str)
            if after == before:
                break

    def _pending(self, session: SessionData) -> list[Requirement]:
        if session.source_system is None:
            systems = self.rule_engine.systems
            return [
                Requirement(
                    path="metadata.sourceSystemGcpId",
                    question="Jaki jest system źródłowy?",
                    reason="source_system",
                    input_mode=self.rule_engine.input_mode("metadata.sourceSystemGcpId"),
                    value_schema={"type": "string", "enum": systems},
                    allowed_values=systems,
                )
            ]
        self._advance(session)
        if not has_path(session.contract, "source.sourceType"):
            choices = self._source_type_choices(session)
            return [
                Requirement(
                    path="source.sourceType",
                    question="Jaki jest typ źródła danych?",
                    reason="one_of",
                    input_mode=self.rule_engine.input_mode("source.sourceType"),
                    value_schema={"type": "string", "enum": choices},
                    allowed_values=choices,
                )
            ]
        requirements = self.navigator.missing_requirements(session.contract)
        for requirement in requirements:
            requirement.input_mode = self.rule_engine.input_mode(requirement.path)
        return requirements

    def _source_type_choices(self, session: SessionData) -> list[str]:
        if session.source_system:
            configured = self.rule_engine.source_types(session.source_system)
            if configured:
                return configured
        return self.navigator.source_type_values()

    def _state(self, session: SessionData) -> ForgeState:
        pending = self._pending(session)
        validation_errors = [] if pending else self.navigator.validate(session.contract)
        status = "needs_input" if pending else ("invalid" if validation_errors else "complete")

        # Re-evaluate rule compatibility against the current active schema for observability.
        rule_issues: list[RuleIssue] = []
        if session.source_system:
            for scope in (Origin.SYSTEM_ENRICHMENT, Origin.GENERIC_ENRICHMENT):
                _, issues = self.rule_engine.apply_pass(
                    deepcopy(session.contract), deepcopy(session.origins), session.source_system, scope
                )
                rule_issues.extend(issues)

        return ForgeState(
            session_id=session.session_id,
            source_system=session.source_system,
            contract=deepcopy(session.contract),
            origins={k: v.value for k, v in session.origins.items()},
            status=status,
            pending=pending,
            validation_errors=validation_errors,
            candidate_issues=deepcopy(session.candidate_issues),
            applied=deepcopy(session.applied[-100:]),
            rule_issues=rule_issues,
        )

    def _get(self, session_id: str) -> SessionData:
        try:
            return self.sessions[session_id]
        except KeyError as exc:
            raise KeyError(f"Unknown Contract Forge session: {session_id}") from exc
