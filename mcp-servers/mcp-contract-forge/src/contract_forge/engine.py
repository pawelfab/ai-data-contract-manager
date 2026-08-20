from __future__ import annotations

import json
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any

from .compiler import compile_contract
from .contract_rules import ContractRuleEngine
from .contracts import ContractSourcePort, InMemoryContractAdapter, JsonFileContractAdapter
from .models import (
    OVERRIDABLE_ORIGINS,
    ContractRuleIssue,
    DiscardedValue,
    EditableField,
    ForgeState,
    Origin,
    Requirement,
    RuleIssue,
    SessionData,
    ValidationIssue,
)
from .path_utils import delete_path, get_path, has_path, write_value
from .rules import RuleEngine

# Writing one of these paths invalidates everything Forge derived from it. A single
# explicit trigger is enough today; a `recompute_trigger` marker in the schema would be
# the better home once more fields influence enrichment.
RECOMPUTE_TRIGGER_PATHS = frozenset({"metadata.sourceSystemGcpId"})


class ContractForge:
    """Canonical owner of contract construction state.

    ADCM never directly mutates the canonical contract. It submits candidate values and
    receives the next set of requirements. Enrichment/default precedence is:

      user > system enrichment > generic enrichment > schema default.

    Deterministic and LLM extraction are ADCM concerns; both submit USER facts.

    Contract definition I/O sits behind ``ContractSourcePort`` and the definition is
    compiled before any session exists, so a contract Forge cannot execute is rejected
    at startup rather than halfway through a conversation.
    """

    def __init__(
        self,
        contract_source: ContractSourcePort | dict[str, Any],
        rules: dict[str, Any],
        deploy_env: str = "dev",
    ):
        # In-memory construction stays supported, but still goes through an adapter.
        if isinstance(contract_source, dict):
            contract_source = InMemoryContractAdapter(contract_source)
        self.contract_source = contract_source
        self.compiled = compile_contract(contract_source)
        self.navigator = self.compiled.navigator
        self.rule_engine = RuleEngine(rules, self.navigator, deploy_env=deploy_env)
        self.contract_rule_engine = ContractRuleEngine(self.compiled)
        self.sessions: dict[str, SessionData] = {}

    @classmethod
    def from_files(cls, schema_path: str | Path, rules_path: str | Path, deploy_env: str = "dev") -> "ContractForge":
        rules = json.loads(Path(rules_path).read_text(encoding="utf-8"))
        return cls(JsonFileContractAdapter(schema_path), rules, deploy_env=deploy_env)

    @classmethod
    def from_dicts(cls, schema: dict[str, Any], rules: dict[str, Any], deploy_env: str = "dev") -> "ContractForge":
        return cls(InMemoryContractAdapter(schema), rules, deploy_env=deploy_env)

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
        session.discarded.clear()
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
        """A user may write any path the active schema resolves, at any time.

        `complete` means the current contract version is complete, not that the session
        is closed, so deliberate edits are not restricted to pending/overridable paths.
        The path still has to exist in the active schema, the value is still validated
        locally, and enrichment origins still lose to USER through ``can_replace``.
        """
        if path in pending:
            return True
        if origin != Origin.USER:
            return False
        return self.navigator.path_exists_in_schema(path, session.contract)

    def _disallowed_path_issue(self, session: SessionData, path: str) -> ValidationIssue:
        if not self.navigator.path_exists_in_schema(path, session.contract):
            return ValidationIssue(
                path=path,
                message="Candidate path does not exist in the active contract schema.",
                validator="path",
            )
        return ValidationIssue(
            path=path,
            message="Candidate path is not currently writable by this origin.",
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
            canonical_value = str(value).strip().upper()
            node = self.navigator.schema_at_path(path, session.contract)
            if node is None:
                return [
                    ValidationIssue(
                        path=path,
                        message="Source-system path does not exist in the contract schema.",
                        validator="path",
                    )
                ]
            local_errors = self.navigator.validate_value(node, canonical_value)
            if local_errors:
                return [
                    issue.model_copy(
                        update={"path": f"{path}.{issue.path}" if issue.path else path}
                    )
                    for issue in local_errors
                ]
            applied = write_value(
                session.contract,
                session.origins,
                path,
                canonical_value,
                origin,
            )
            previous_system = session.source_system
            if not applied:
                return [ValidationIssue(path=path, message="Candidate lost origin precedence.", validator="precedence")]
            session.source_system = canonical_value.lower()
            session.applied.append(applied)
            if previous_system is not None and previous_system != session.source_system:
                self._recompute_derived_values(session)
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
        if origin == Origin.USER:
            self._invalidate_dependents(session, path)
        return []

    def _invalidate_dependents(self, session: SessionData, changed_path: str) -> None:
        """Drop enrichment values derived from a path the user just changed.

        Enrichment is fill-only, so without this a corrected input would leave its
        derived values stale — adding a source column would not reach the target table.
        Values the user set themselves are never touched.
        """
        pending = [changed_path]
        seen: set[str] = set()
        while pending:
            source_path = pending.pop()
            if source_path in seen:
                continue
            seen.add(source_path)
            for target in self.rule_engine.dependent_paths(source_path, session.source_system):
                if session.origins.get(target) not in OVERRIDABLE_ORIGINS:
                    continue
                delete_path(session.contract, target)
                session.origins.pop(target, None)
                pending.append(target)

    def _recompute_derived_values(self, session: SessionData) -> None:
        """Rebuild everything Forge derived after a recompute trigger changed.

        Provenance makes this cheap: drop the values Forge itself produced, re-run
        enrichment for the new context, then drop whatever no longer belongs to the
        active schema variant. Values the user stated are kept — changing the source
        system must not cost them the pipeline name, owner or schedule.
        """
        removed: list[DiscardedValue] = []
        for path in sorted(session.origins, key=lambda item: item.count("."), reverse=True):
            origin = session.origins[path]
            if origin not in OVERRIDABLE_ORIGINS:
                continue
            removed.append(
                DiscardedValue(
                    path=path,
                    previous_value=deepcopy(get_path(session.contract, path, None)),
                    origin=origin,
                    reason="recompute",
                )
            )
            delete_path(session.contract, path)
            session.origins.pop(path, None)

        self._advance(session)
        self._prune_inactive_branch(session)

        # Most derived values are recalculated to the same thing. Only report what the
        # user actually lost, otherwise the warning drowns in noise.
        session.discarded.extend(
            entry
            for entry in removed
            if get_path(session.contract, entry.path, None) != entry.previous_value
        )

    def _prune_inactive_branch(self, session: SessionData) -> None:
        """Drop values that the newly active schema variant no longer knows.

        Only runs once the source discriminator is resolved: under an unresolved
        ``oneOf`` nothing below ``source`` resolves, and pruning then would also delete
        correct values such as ``source.uri``.
        """
        if not has_path(session.contract, "source.sourceType"):
            return
        for path in sorted(session.origins, key=lambda item: item.count("."), reverse=True):
            if self.navigator.path_exists_in_schema(path, session.contract):
                continue
            session.discarded.append(
                DiscardedValue(
                    path=path,
                    previous_value=deepcopy(get_path(session.contract, path, None)),
                    origin=session.origins[path],
                    reason="inactive_branch",
                )
            )
            delete_path(session.contract, path)
            session.origins.pop(path, None)

    def _advance(self, session: SessionData) -> None:
        if session.source_system is None:
            return

        # Required objects are structural, not user decisions.
        self.navigator.ensure_required_containers(session.contract, session.origins)

        # Run to a fixpoint because later rules can become eligible after earlier rules/defaults.
        known_source_system = session.source_system in self.rule_engine.systems
        for _ in range(8):
            before = json.dumps(session.contract, sort_keys=True, default=str)
            if known_source_system:
                session.applied.extend(
                    self.rule_engine.apply_system_source_type(
                        session.contract,
                        session.origins,
                        session.source_system,
                    )
                )

                applied, _ = self.rule_engine.apply_pass(
                    session.contract,
                    session.origins,
                    session.source_system,
                    Origin.SYSTEM_ENRICHMENT,
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

    def _pending(
        self,
        session: SessionData,
        contract_rule_issues: list[ContractRuleIssue] | None = None,
    ) -> list[Requirement]:
        if session.source_system is None:
            systems = self.rule_engine.systems
            node = self.navigator.schema_at_path(
                "metadata.sourceSystemGcpId",
                session.contract,
            )
            return [
                Requirement(
                    path="metadata.sourceSystemGcpId",
                    question="Jaki jest system źródłowy?",
                    reason="source_system",
                    input_mode=self.rule_engine.input_mode("metadata.sourceSystemGcpId"),
                    value_schema=(
                        self.navigator.public_schema(node)
                        if node is not None
                        else {"type": "string", "minLength": 1}
                    ),
                    allowed_values=systems,
                    allow_custom_value=True,
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
        requirements = self.navigator.dedupe_requirements(
            [
                *self.navigator.missing_requirements(session.contract),
                *self.contract_rule_engine.missing_requirements(
                    session.contract, contract_rule_issues
                ),
            ]
        )
        for requirement in requirements:
            requirement.input_mode = self.rule_engine.input_mode(requirement.path)
        return requirements

    def _source_type_choices(self, session: SessionData) -> list[str]:
        if session.source_system:
            configured = self.rule_engine.source_types(session.source_system)
            if configured:
                return configured
        return self.navigator.source_type_values()

    def editable_fields(self, session_id: str) -> list[EditableField]:
        """List the units of deliberate change in the current contract.

        Separate from ``overridable``: that one drives automatic filling of derived
        values, this one is the surface for changes the user asks for, whatever the
        provenance. Served through its own MCP tool rather than every ForgeState so the
        ordinary stair-step loop does not carry the whole catalogue.
        """
        session = self._get(session_id)
        fields: list[EditableField] = []

        def walk(value: Any, path: str) -> None:
            node = self.navigator.schema_at_path(path, session.contract) if path else self.navigator.schema
            if node is None:
                return
            # An array is one atomic edit unit: replacing the whole value keeps
            # provenance and validation simple and avoids per-index paths.
            if isinstance(value, dict) and node.get("type") != "array":
                for name, child in value.items():
                    walk(child, f"{path}.{name}" if path else name)
                return
            if not path:
                return
            fields.append(
                EditableField(
                    path=path,
                    current_value=deepcopy(value),
                    value_schema=self.navigator.public_schema(node),
                    description=node.get("x-acdm-question") or node.get("description"),
                    allowed_values=self.navigator.allowed_values(node),
                    unsupported_schema_keywords=self.navigator.unsupported_requirement_keywords(node),
                    current_origin=session.origins.get(path),
                )
            )

        walk(session.contract, "")
        return sorted(fields, key=lambda field: field.path)

    def _overridable(self, session: SessionData) -> list[Requirement]:
        """Expose existing values the user may replace through Forge."""
        fields: list[Requirement] = []
        for path, origin in sorted(session.origins.items()):
            if (
                origin not in OVERRIDABLE_ORIGINS | {Origin.USER}
                or path == "metadata.sourceSystemGcpId"
                or not has_path(session.contract, path)
            ):
                continue
            requirement = self.navigator.requirement_at_path(path, session.contract)
            if requirement is None:
                continue
            input_mode = self.rule_engine.input_mode(path)
            if (
                origin == Origin.USER
                and (
                    input_mode == "explicit"
                    or requirement.value_schema.get("type") in {"array", "object"}
                )
            ):
                # Explicit gates require their dedicated confirmation flow. Canonical
                # structures may contain nested defaults/enrichments that are not
                # part of the user's raw fact and stay on the pending/partial flow.
                continue
            fields.append(
                requirement.model_copy(
                    update={
                        "input_mode": input_mode,
                        "current_value": deepcopy(get_path(session.contract, path)),
                        "current_origin": origin,
                    }
                )
            )
        return fields

    def _state(self, session: SessionData) -> ForgeState:
        # Evaluate the contract rules once and reuse the result for both requirement
        # discovery and diagnostics.
        contract_rule_issues = (
            self.contract_rule_engine.evaluate(session.contract) if session.source_system else []
        )
        pending = self._pending(session, contract_rule_issues)
        validation_errors = [] if pending else self.navigator.validate(session.contract)
        blocking_rules = [] if pending else self.contract_rule_engine.blocking_issues(contract_rule_issues)
        status = (
            "needs_input"
            if pending
            else ("invalid" if validation_errors or blocking_rules else "complete")
        )

        # Re-evaluate rule compatibility against the current active schema for observability.
        rule_issues: list[RuleIssue] = []
        if session.source_system:
            scopes = [Origin.GENERIC_ENRICHMENT]
            if session.source_system in self.rule_engine.systems:
                scopes.insert(0, Origin.SYSTEM_ENRICHMENT)
            for scope in scopes:
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
            overridable=self._overridable(session),
            validation_errors=validation_errors,
            candidate_issues=deepcopy(session.candidate_issues),
            applied=deepcopy(session.applied[-100:]),
            discarded=deepcopy(session.discarded),
            rule_issues=rule_issues,
            contract_rule_issues=deepcopy(contract_rule_issues),
        )

    def _get(self, session_id: str) -> SessionData:
        try:
            return self.sessions[session_id]
        except KeyError as exc:
            raise KeyError(f"Unknown Contract Forge session: {session_id}") from exc
