from __future__ import annotations

import json
import uuid
from typing import Any

from .gateway import ForgeGateway
from .heuristics import HeuristicResolver
from .models import (
    AssistantTurn,
    ChatMessage,
    ConversationMemory,
    ExtractionMethod,
    ForgeState,
    Origin,
    PartialFact,
    Requirement,
    UserFact,
    ValidationIssue,
)
from .semantic import NoopSemanticResolver, SemanticResolver


class ADCMOrchestrator:
    """Thin conversational orchestrator between user/LLM and Contract Forge."""

    def __init__(
        self,
        gateway: ForgeGateway,
        semantic: SemanticResolver | None = None,
        heuristics: HeuristicResolver | None = None,
        max_auto_steps: int = 12,
    ):
        self.gateway = gateway
        # The resolver remains a runtime dependency but Stage 03 deliberately does
        # not call it. Deterministic extraction is exhausted and then the user is asked.
        self.semantic = semantic or NoopSemanticResolver()
        self.heuristics = heuristics or HeuristicResolver()
        self.max_auto_steps = max_auto_steps
        self.sessions: dict[str, ConversationMemory] = {}

    async def start(self) -> AssistantTurn:
        forge_state = await self.gateway.start_session()
        session_id = str(uuid.uuid4())
        memory = ConversationMemory(session_id=session_id, forge_session_id=forge_state.session_id)
        self.sessions[session_id] = memory
        turn = self._turn_from_state(session_id, forge_state, memory)
        memory.add_assistant_message(turn.message)
        return turn

    async def message(self, session_id: str, text: str) -> AssistantTurn:
        memory = self.sessions[session_id]
        user_message = memory.add_user_message(text)
        state = await self.gateway.get_state(memory.forge_session_id)
        fields = self._resolvable_fields(state)
        primary_path = state.pending[0].path if state.pending else None

        # Only the first pending field accepts an unlabeled direct answer. Historical
        # extraction and overrides stay strict so an old answer is not assigned to a
        # requirement that Forge exposed later.
        values: dict[str, Any] = {}
        if state.pending:
            values.update(
                self.heuristics.extract(
                    text,
                    state.pending[:1],
                    state.contract,
                    allow_plain_fallback=True,
                )
            )
        remaining = [
            field
            for field in fields
            if primary_path is None or field.path != primary_path
        ]
        if remaining:
            values.update(
                self.heuristics.extract(
                    text,
                    remaining,
                    state.contract,
                    allow_plain_fallback=False,
                    allow_structured=False,
                )
            )
        self._merge_current_structured(
            memory,
            user_message,
            text,
            fields,
            primary_path,
            values,
        )
        self._remember_deterministic(memory, user_message, values)

        state = await self._auto_resolve(memory, state)
        turn = self._turn_from_state(session_id, state, memory)
        memory.add_assistant_message(turn.message)
        return turn

    async def _auto_resolve(
        self,
        memory: ConversationMemory,
        state: ForgeState,
    ) -> ForgeState:
        attempted: set[tuple[str, str]] = set()

        for _ in range(self.max_auto_steps):
            fields = self._resolvable_fields(state)
            if not fields:
                break

            # UserFact is the primary source. History is scanned only when no stored
            # fact matches any field currently exposed by Forge.
            candidate = self._candidate_from_facts(memory, fields)
            if candidate is None:
                self._scan_history(
                    memory,
                    fields,
                    state.contract,
                    structured_paths=(
                        {state.pending[0].path} if state.pending else set()
                    ),
                )
                candidate = self._candidate_from_facts(memory, fields)
            if candidate is None:
                break

            path, value = candidate
            candidate_key = (path, json.dumps(value, sort_keys=True, default=str))
            if candidate_key in attempted:
                state = self._with_candidate_issue(
                    state,
                    ValidationIssue(
                        path=path,
                        message="Ten sam kandydat został już odrzucony; automatyczne rozwiązywanie przerwano.",
                        validator="repeated_candidate",
                    ),
                )
                break
            attempted.add(candidate_key)

            before = self._state_signature(state)
            new_state = await self.gateway.submit_values(
                memory.forge_session_id,
                {path: value},
                Origin.USER,
            )
            if new_state.candidate_issues:
                state = new_state
                break
            if self._state_signature(new_state) == before:
                state = self._with_candidate_issue(
                    new_state,
                    ValidationIssue(
                        path=path,
                        message="Contract Forge nie zastosował kandydata; automatyczne rozwiązywanie przerwano.",
                        validator="no_progress",
                    ),
                )
                break
            memory.clear_partial(path)
            state = new_state
        else:
            state = self._with_candidate_issue(
                state,
                ValidationIssue(
                    path="",
                    message="Osiągnięto limit automatycznych kroków; potrzebna jest odpowiedź użytkownika.",
                    validator="max_auto_steps",
                ),
            )

        return state

    def _merge_current_structured(
        self,
        memory: ConversationMemory,
        message: ChatMessage,
        text: str,
        fields: list[Requirement],
        primary_path: str | None,
        values: dict[str, Any],
    ) -> None:
        if message.message_sequence is None:
            return
        for field in fields:
            parsed = self.heuristics.parse_structured(text, field)
            if parsed is None:
                continue
            existing = memory.get_partial(field.path)
            is_primary = field.path == primary_path
            if not is_primary and existing is None:
                # The same pasted table can satisfy several schema-compatible paths
                # with different meanings. Without an explicit partial already in
                # progress, bind it only to Forge's first current requirement.
                continue
            merged = (
                self.heuristics.merge_structured(existing.value, parsed, field)
                if existing is not None
                else parsed
            )
            memory.remember_partial(
                PartialFact(
                    path=field.path,
                    value=merged.value,
                    missing=merged.missing,
                    invalid=merged.invalid,
                    message_sequence=message.message_sequence,
                    evidence=message.content,
                )
            )
            if merged.complete:
                values[field.path] = merged.value
            else:
                values.pop(field.path, None)
                memory.forget_fact(field.path)

    def _scan_history(
        self,
        memory: ConversationMemory,
        fields: list[Requirement],
        contract: dict[str, Any],
        *,
        structured_paths: set[str],
    ) -> None:
        # Scan everything before selecting a candidate. ConversationMemory then
        # enforces latest-user-message wins independently for every path.
        for message in reversed(memory.messages):
            if message.role != "user":
                continue
            found = self.heuristics.extract(
                message.content,
                fields,
                contract,
                allow_plain_fallback=False,
                allow_structured=False,
            )
            structured_fields = [
                field for field in fields if field.path in structured_paths
            ]
            if structured_fields:
                found.update(
                    self.heuristics.extract(
                        message.content,
                        structured_fields,
                        contract,
                        allow_plain_fallback=False,
                        allow_structured=True,
                    )
                )
            self._remember_deterministic(memory, message, found)

    async def state(self, session_id: str) -> ForgeState:
        memory = self.sessions[session_id]
        return await self.gateway.get_state(memory.forge_session_id)

    @staticmethod
    def _resolvable_fields(state: ForgeState) -> list[Requirement]:
        fields: list[Requirement] = []
        seen: set[str] = set()
        for field in [*state.pending, *state.overridable]:
            if field.path not in seen:
                seen.add(field.path)
                fields.append(field)
        return fields

    @staticmethod
    def _candidate_from_facts(
        memory: ConversationMemory,
        fields: list[Requirement],
    ) -> tuple[str, Any] | None:
        for field in fields:
            fact = memory.get_fact(field.path)
            if fact is not None:
                return field.path, fact.value
        return None

    @staticmethod
    def _state_signature(state: ForgeState) -> str:
        resolution_state = {
            "status": state.status,
            "contract": state.contract,
            "origins": state.origins,
            "pending": [field.model_dump(mode="json") for field in state.pending],
            "overridable": [field.model_dump(mode="json") for field in state.overridable],
        }
        return json.dumps(resolution_state, sort_keys=True, default=str)

    @staticmethod
    def _with_candidate_issue(state: ForgeState, issue: ValidationIssue) -> ForgeState:
        return state.model_copy(
            update={"candidate_issues": [*state.candidate_issues, issue]},
            deep=True,
        )

    @staticmethod
    def _remember_deterministic(
        memory: ConversationMemory,
        message: ChatMessage,
        values: dict[str, Any],
    ) -> None:
        if message.message_sequence is None:
            return
        for path, value in values.items():
            memory.remember_fact(
                UserFact(
                    path=path,
                    value=value,
                    message_sequence=message.message_sequence,
                    extraction_method=ExtractionMethod.DETERMINISTIC,
                    evidence=message.content,
                )
            )

    @staticmethod
    def _candidate_issue_summary(state: ForgeState) -> str:
        return "; ".join(
            f"{issue.path or '<root>'}: {issue.message}"
            for issue in state.candidate_issues[:3]
        )

    @staticmethod
    def _partial_question(requirement: Requirement, partial: PartialFact) -> str:
        records = partial.value if isinstance(partial.value, list) else []
        item_schema = requirement.value_schema.get("items", {})
        properties = item_schema.get("properties", {})
        required = item_schema.get("required", [])
        identity = "name" if "name" in properties else next(
            (
                name
                for name in required
                if properties.get(name, {}).get("type") == "string"
                and not properties.get(name, {}).get("enum")
            ),
            None,
        )

        details: list[str] = []
        for missing in partial.missing:
            labels = [
                str(record.get(identity, index + 1))
                for index, record in enumerate(records)
                if isinstance(record, dict) and missing not in record
            ]
            suffix = f" dla: {', '.join(labels)}" if labels else ""
            details.append(f"{missing}{suffix}")

        count = len(records)
        if count == 1:
            count_label = "1 element"
        elif count % 10 in {2, 3, 4} and count % 100 not in {12, 13, 14}:
            count_label = f"{count} elementy"
        else:
            count_label = f"{count} elementów"
        message = f"Rozpoznałem {count_label} dla {requirement.path}."
        if details:
            message += f" Brakuje wymaganych danych: {'; '.join(details)}."
        else:
            message += " Dane wymagają doprecyzowania."
        if partial.invalid:
            message += f" Nie rozpoznałem wartości: {', '.join(partial.invalid)}."

        if identity and required:
            format_hint = " ".join(required)
            example_name = next(
                (
                    str(record[identity])
                    for record in records
                    if isinstance(record, dict) and record.get(identity)
                ),
                identity,
            )
            example_values = [example_name]
            for name in required:
                if name == identity:
                    continue
                schema = properties.get(name, {})
                enum = schema.get("enum")
                if isinstance(enum, list) and enum:
                    example_values.append(str(enum[0]))
                elif schema.get("type") == "integer":
                    example_values.append("0")
                else:
                    example_values.append(name)
            message += (
                f" Podaj brakujące dane w układzie „{format_hint}”, "
                f"np. {' '.join(example_values)}."
            )

        allowed_parts = [
            f"{name}: {', '.join(map(str, schema['enum']))}"
            for name, schema in properties.items()
            if name in partial.missing and isinstance(schema.get("enum"), list)
        ]
        if allowed_parts:
            message += f" Dozwolone wartości — {'; '.join(allowed_parts)}."
        return message

    @classmethod
    def _turn_from_state(
        cls,
        session_id: str,
        state: ForgeState,
        memory: ConversationMemory,
    ) -> AssistantTurn:
        candidate_issues = [issue.model_dump(mode="json") for issue in state.candidate_issues]
        issue_summary = cls._candidate_issue_summary(state)

        if state.status == "complete":
            message = "Kontrakt jest kompletny i przeszedł walidację Contract Forge."
            if issue_summary:
                message += f" Nie zastosowano jednak części danych użytkownika: {issue_summary}"
            return AssistantTurn(
                session_id=session_id,
                message=message,
                status="complete",
                contract=state.contract,
                candidate_issues=candidate_issues,
            )
        if state.status == "invalid":
            details = "; ".join(
                f"{error.path or '<root>'}: {error.message}"
                for error in state.validation_errors[:5]
            )
            return AssistantTurn(
                session_id=session_id,
                message=f"Contract Forge zakończył kompletowanie, ale kontrakt jest niepoprawny: {details}",
                status="invalid",
                contract=state.contract,
                validation_errors=[error.model_dump(mode="json") for error in state.validation_errors],
                candidate_issues=candidate_issues,
            )

        requirement = state.pending[0] if state.pending else None
        if requirement is None:
            question = "Contract Forge potrzebuje dodatkowych danych."
            suffix = ""
        else:
            partial = memory.get_partial(requirement.path)
            question = (
                cls._partial_question(requirement, partial)
                if partial is not None and (partial.missing or partial.invalid)
                else requirement.question
            )
            suffix = (
                f" Dostępne: {', '.join(map(str, requirement.allowed_values))}."
                if requirement.allowed_values
                else ""
            )
        if issue_summary:
            question = f"Nie udało się zastosować podanej wartości ({issue_summary}). {question}"
        return AssistantTurn(
            session_id=session_id,
            message=question + suffix,
            status="needs_input",
            pending_path=requirement.path if requirement else None,
            contract=state.contract,
            candidate_issues=candidate_issues,
        )
