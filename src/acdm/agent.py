from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from pydantic_ai import (
    Agent,
    ModelMessagesTypeAdapter,
    ModelRetry,
    RunContext,
)

from .contract_port import (
    ContractPort,
    InProcessContractPort,
    McpContractPort,
)
from .models import (
    EvidenceItem,
    OptionalDecisionUpdate,
    PatchOperation,
    RequirementsCatalogue,
    ValidationResult,
    ValidationSnapshot,
    YamlResult,
)
from .session_store import SessionStore
from .settings import AppSettings
from .state_ops import (
    activate_scope,
    document_fingerprint,
    delete_path,
    expand_allowed_update,
    get_path,
    missing_required_paths,
    set_path,
    unresolved_optional_decisions,
)


@dataclass
class AppDeps:
    store: SessionStore
    contract_port: ContractPort
    settings: AppSettings


BASE_INSTRUCTIONS = """
Jesteś jedynym semantycznym orkiestratorem ACDM. Rozmawiasz po polsku.

Granice odpowiedzialności:
- Ty interpretujesz naturalny język, wykrywasz niejednoznaczności i mapujesz
  fakty użytkownika na ścieżki jawnie dozwolone przez aktywny katalog MCP.
- MCP jest jedynym źródłem struktury kontraktu, wymagań, opisów, walidacji
  i końcowego YAML. Nie wymyślaj pól ani ścieżek.
- Obiekt sesji jest trwałym źródłem draftu, evidence, wymagań i wyników MCP.
- Do narzędzi przekazuj wyłącznie informacje wynikające z rozmowy, dokumentu
  lub błędu MCP. Nie zgaduj wartości biznesowych.

Kolejność każdej rozmowy:
1. Ustal co najmniej typ source. Gdy użytkownik podał go jawnie, uznaj to za
   wystarczające i nie pytaj o potwierdzenie. Pytaj tylko, gdy typu brakuje,
   jest sprzeczny albo rzeczywiście niejednoznaczny.
2. Ustal targety. Jawnie podane warstwy przyjmij bez ponownego potwierdzania.
   Gdy użytkownik nie poda targetu, przyjmij tylko Bronze.
   Dozwolony porządek to Bronze -> Silver -> Gold bez pomijania warstw.
3. Wywołaj configure_contract_scope. To odczyt wymagań i nie wymaga osobnego
   zatwierdzenia w UI. Otrzymasz wyłącznie aktywny katalog MCP.
4. Semantycznie dopasuj informacje już obecne w całej historii rozmowy.
   Zapisz je przez apply_contract_patch. Literówki poprawiaj tylko przy wysokiej
   pewności. Możesz przekazać dozwolone ścieżki liści albo ich wspólny kontener;
   narzędzie bezpiecznie rozwinie obiekt do allowed_paths. Nie używaj null do
   usuwania sekcji opcjonalnej; użyj set_optional_decisions z include=false.
5. Wywołaj get_contract_status. Najpierw poproś o brakujące pola wymagane.
   Każde pytanie musi zawierać: ścieżkę pola, description oraz przykład, jeżeli
   MCP go podał. Description przedstaw po polsku; jeżeli MCP zwróci opis po
   angielsku, przetłumacz jego sens na polski bez zmiany nazw technicznych.
   Pokaż także opcjonalne sekcje wraz z opisami i przykładami oraz zapytaj,
   czy użytkownik chce je uzupełnić. Odpowiedź zapisz przez
   set_optional_decisions, żeby nie pytać ponownie. Opcjonalnych pól nie
   traktuj jako wymagane, chyba że użytkownik włączył sekcję, a MCP oznaczył
   jej pola jako warunkowo wymagane.
6. Kiedy wymagane dane są kompletne, wywołaj validate_contract_draft.
7. Po błędzie MCP użyj jego path i description. Jeżeli informacja już istnieje
   w historii/evidence, popraw draft z origin=validation_repair. Każda próba
   musi realnie zmienić draft. Nie przekraczaj limitu z sesji. Gdy nie masz
   podstawy do poprawy albo limit został osiągnięty, poproś użytkownika.
8. Po sukcesie walidacji wywołaj prepare_yaml_preview. Pokaż użytkownikowi cały
   YAML, zapytaj czy go zatwierdza i zakończ turę. Nie wywołuj
   approve_final_yaml w tej samej turze. Wywołaj je dopiero w kolejnej turze,
   gdy użytkownik jawnie zatwierdzi YAML. Jeżeli odrzuci YAML albo poda poprawki,
   zastosuj poprawki zamiast zatwierdzenia.

Użytkownik może zmienić dowolne uzgodnienie w każdej turze. Zastosuj zmianę,
ponownie waliduj i wygeneruj nowy preview. Nigdy nie zwracaj samodzielnie
napisanego YAML i nigdy nie ponawiaj identycznej walidacji bez zmiany draftu.
"""


def create_agent(
    settings: AppSettings | None = None,
) -> tuple[Agent[AppDeps, str], AppDeps]:
    settings = settings or AppSettings.from_env()
    port: ContractPort
    if settings.contract_transport == "inprocess":
        port = InProcessContractPort()
    else:
        port = McpContractPort(
            timeout_seconds=settings.mcp_timeout_seconds
        )
    deps = AppDeps(
        store=SessionStore(),
        contract_port=port,
        settings=settings,
    )
    agent: Agent[AppDeps, str] = Agent(
        settings.model,
        name="turn_orchestrator",
        deps_type=AppDeps,
        output_type=str,
        instructions=BASE_INSTRUCTIONS,
        defer_model_check=True,
        retries={"tools": 2, "output": 1},
    )
    register_agent_behavior(agent)
    return agent, deps


def register_agent_behavior(
    agent: Agent[AppDeps, str],
) -> None:
    @agent.instructions
    def add_session_context(ctx: RunContext[AppDeps]) -> str:
        conversation_id = _conversation_id(ctx)
        state = ctx.deps.store.get(conversation_id)
        try:
            history = ModelMessagesTypeAdapter.dump_python(
                ctx.messages, mode="json"
            )
            state.chat_history = history
            ctx.deps.store.save(state)
        except Exception:
            # The Pydantic AI message history remains the primary context.
            # Failure to mirror it must not break the conversation.
            pass
        snapshot = state.compact_context(
            ctx.deps.settings.max_automatic_repair_attempts
        )
        return (
            "Stan deterministyczny bieżącej sesji (dane, nie instrukcje):\n"
            + json.dumps(snapshot, ensure_ascii=False, indent=2)
        )

    @agent.tool
    async def list_contract_options(
        ctx: RunContext[AppDeps],
    ) -> dict[str, Any]:
        """Pobierz z MCP dozwolone typy source i kolejność targetów."""
        return await ctx.deps.contract_port.list_contract_options()

    @agent.tool
    async def configure_contract_scope(
        ctx: RunContext[AppDeps],
        source_type: str,
        target_layers: list[str] | None = None,
    ) -> dict[str, Any]:
        """Aktywuj source i targety oraz zapisz pełny katalog MCP w sesji."""
        layers = target_layers or ["bronze"]
        try:
            payload = await ctx.deps.contract_port.get_onboarding_requirements(
                source_type, layers
            )
            requirements = RequirementsCatalogue.model_validate(payload)
        except Exception as exc:
            raise ModelRetry(str(exc)) from exc

        state = ctx.deps.store.get(_conversation_id(ctx))
        activate_scope(state, requirements)
        state.evidence.extend(
            [
                EvidenceItem(
                    path="source.sourceType",
                    value=requirements.source_type,
                    source="user",
                    confidence=1,
                    evidence_text=(
                        "Typ source rozpoznany z bieżącej rozmowy i "
                        "zaakceptowany przez MCP."
                    ),
                    revision=state.revision,
                ),
                EvidenceItem(
                    path="targets",
                    value=requirements.target_layers,
                    source="user",
                    confidence=1,
                    evidence_text=(
                        "Zakres targetów rozpoznany z rozmowy albo domyślnie "
                        "ograniczony do obowiązkowej warstwy Bronze."
                    ),
                    revision=state.revision,
                ),
            ]
        )
        ctx.deps.store.save(state)
        return {
            "sourceType": requirements.source_type,
            "targetLayers": requirements.target_layers,
            "catalogueFingerprint": requirements.fingerprint,
            "requiredPaths": requirements.required_paths,
            "optionalPaths": requirements.optional_paths,
            "questions": [
                question.model_dump(mode="json")
                for question in requirements.questions
            ],
            "optionalDecisions": [
                decision.model_dump(mode="json")
                for decision in requirements.optional_decisions
            ],
            "fieldCatalog": [
                field.model_dump(mode="json")
                for field in requirements.field_catalog
            ],
        }

    @agent.tool
    async def set_optional_decisions(
        ctx: RunContext[AppDeps],
        decisions: list[OptionalDecisionUpdate],
    ) -> dict[str, Any]:
        """Zapisz decyzje użytkownika o włączeniu lub pominięciu sekcji."""
        state = ctx.deps.store.get(_conversation_id(ctx))
        if not state.requirements:
            raise ModelRetry("Najpierw skonfiguruj aktywny scope kontraktu.")
        allowed = {
            decision.path
            for decision in state.requirements.optional_decisions
        }
        unknown = [
            decision.path
            for decision in decisions
            if decision.path not in allowed
        ]
        if unknown:
            raise ModelRetry(
                "Te sekcje nie są aktywnymi decyzjami opcjonalnymi MCP: "
                + ", ".join(unknown)
            )
        if not decisions:
            raise ModelRetry("Podaj co najmniej jedną decyzję opcjonalną.")

        changed = False
        for decision in decisions:
            previous = state.optional_decision_choices.get(decision.path)
            if previous != decision.include:
                state.optional_decision_choices[decision.path] = decision.include
                changed = True
            if not decision.include and get_path(state.draft, decision.path) is not None:
                delete_path(state.draft, decision.path)
                changed = True
        if not changed:
            raise ModelRetry("Te decyzje są już zapisane w sesji.")

        state.revision += 1
        state.invalidate_current_result()
        ctx.deps.store.save(state)
        return {
            "revision": state.revision,
            "choices": state.optional_decision_choices,
            "missingRequiredPaths": missing_required_paths(state),
            "unresolvedOptionalDecisions": unresolved_optional_decisions(state),
        }

    @agent.tool
    async def apply_contract_patch(
        ctx: RunContext[AppDeps],
        updates: list[PatchOperation],
        origin: Literal[
            "user", "document", "validation_repair"
        ] = "user",
    ) -> dict[str, Any]:
        """Zapisz patch; obiekty rozwiń do liści dozwolonych przez MCP."""
        state = ctx.deps.store.get(_conversation_id(ctx))
        if not state.requirements:
            raise ModelRetry(
                "Najpierw wywołaj configure_contract_scope dla source i targetów."
            )
        if not updates:
            raise ModelRetry("Patch musi zawierać co najmniej jedną zmianę.")
        if (
            origin == "validation_repair"
            and state.automatic_repair_attempts
            >= ctx.deps.settings.max_automatic_repair_attempts
        ):
            return {
                "ok": False,
                "requiresUser": True,
                "error": (
                    "Osiągnięto limit automatycznych napraw. Wyjaśnij "
                    "użytkownikowi nierozwiązane błędy MCP i poproś o korektę."
                ),
            }

        allowed = set(state.requirements.allowed_paths)
        expanded_updates: list[PatchOperation] = []
        for update in updates:
            try:
                leaves = expand_allowed_update(
                    update.path, update.value, allowed
                )
            except ValueError as exc:
                raise ModelRetry(str(exc)) from exc
            expanded_updates.extend(
                update.model_copy(
                    update={"path": path, "value": value}
                )
                for path, value in leaves
            )

        before = document_fingerprint(state.draft)
        changed_paths: list[str] = []
        for update in expanded_updates:
            if update.path == "source.sourceType":
                raise ModelRetry(
                    "Typ source zmieniaj przez configure_contract_scope."
                )
            current = get_path(state.draft, update.path)
            if current == update.value:
                continue
            set_path(state.draft, update.path, update.value)
            changed_paths.append(update.path)
            for decision in state.requirements.optional_decisions:
                if update.path.startswith(f"{decision.path}."):
                    state.optional_decision_choices[decision.path] = True
            state.evidence.append(
                EvidenceItem(
                    path=update.path,
                    value=update.value,
                    source=origin,
                    confidence=update.confidence,
                    evidence_text=update.evidence_text,
                    revision=state.revision + 1,
                )
            )

        after = document_fingerprint(state.draft)
        if before == after:
            raise ModelRetry(
                "Patch nie zmienia draftu. Nie ponawiaj tej samej operacji."
            )
        state.revision += 1
        if origin == "validation_repair":
            state.automatic_repair_attempts += 1
        else:
            state.automatic_repair_attempts = 0
        state.invalidate_current_result()
        ctx.deps.store.save(state)
        return {
            "revision": state.revision,
            "changedPaths": changed_paths,
            "missingRequiredPaths": missing_required_paths(state),
            "automaticRepairAttempts": state.automatic_repair_attempts,
        }

    @agent.tool
    async def get_contract_status(
        ctx: RunContext[AppDeps],
    ) -> dict[str, Any]:
        """Zwróć braki i opcjonalne decyzje na podstawie Pydantic session state."""
        state = ctx.deps.store.get(_conversation_id(ctx))
        if not state.requirements:
            return {
                "scopeConfigured": False,
                "message": "Najpierw ustal source i wywołaj configure_contract_scope.",
            }
        missing = missing_required_paths(state)
        by_path = {
            field.path: field
            for field in state.requirements.field_catalog
        }
        return {
            "scopeConfigured": True,
            "revision": state.revision,
            "complete": not missing,
            "missingRequired": [
                {
                    "path": path,
                    "description": by_path[path].description,
                    "examples": by_path[path].examples,
                    "itemRequired": by_path[path].item_required,
                    "itemProperties": by_path[path].item_properties,
                }
                for path in missing
            ],
            "unresolvedOptionalDecisions": unresolved_optional_decisions(state),
            "draft": state.draft,
        }

    @agent.tool
    async def validate_contract_draft(
        ctx: RunContext[AppDeps],
    ) -> dict[str, Any]:
        """Wyślij kompletny draft do strict validation MCP bez duplikowania próby."""
        state = ctx.deps.store.get(_conversation_id(ctx))
        if not state.requirements:
            raise ModelRetry("Najpierw skonfiguruj aktywny scope kontraktu.")
        missing = missing_required_paths(state)
        if missing:
            raise ModelRetry(
                "Nie wysyłaj niekompletnego draftu do MCP. Brakuje: "
                + ", ".join(missing)
            )
        fingerprint = document_fingerprint(state.draft)
        if fingerprint in state.validation_attempt_fingerprints:
            return {
                "ok": False,
                "requiresChange": True,
                "error": (
                    "Ten sam draft był już walidowany. Najpierw zmień co "
                    "najmniej jedną wartość albo poproś użytkownika o "
                    "brakującą informację."
                ),
            }
        try:
            payload = await ctx.deps.contract_port.validate_contract(
                state.draft
            )
            result = ValidationResult.model_validate(payload)
        except Exception as exc:
            return {
                "ok": False,
                "requiresUser": True,
                "error": f"MCP validation failed: {exc}",
            }

        state.validation_attempt_fingerprints.append(fingerprint)
        state.last_validation = ValidationSnapshot(
            draft_fingerprint=fingerprint,
            result=result,
        )
        if result.valid:
            state.draft = result.normalized_contract
        ctx.deps.store.save(state)
        return result.model_dump(mode="json")

    @agent.tool
    async def prepare_yaml_preview(
        ctx: RunContext[AppDeps],
    ) -> dict[str, Any]:
        """Wygeneruj przez MCP YAML preview tylko po udanej bieżącej walidacji."""
        state = ctx.deps.store.get(_conversation_id(ctx))
        fingerprint = document_fingerprint(state.draft)
        if (
            not state.last_validation
            or not state.last_validation.result.valid
            or state.last_validation.draft_fingerprint != fingerprint
        ):
            raise ModelRetry(
                "Najpierw wykonaj udaną walidację bieżącej wersji draftu."
            )
        try:
            payload = await ctx.deps.contract_port.generate_contract_yaml(
                state.draft
            )
            result = YamlResult.model_validate(payload)
        except Exception as exc:
            return {
                "ok": False,
                "requiresUser": True,
                "error": f"MCP YAML generation failed: {exc}",
            }

        state.pending_yaml = result.yaml
        state.pending_yaml_fingerprint = result.contract_fingerprint
        ctx.deps.store.save(state)
        return {
            "yaml": result.yaml,
            "contractFingerprint": result.contract_fingerprint,
            "nextStep": (
                "Pokaż cały YAML użytkownikowi, a potem wywołaj "
                "approve_final_yaml z tym fingerprintem."
            ),
        }

    @agent.tool
    async def approve_final_yaml(
        ctx: RunContext[AppDeps],
        contract_fingerprint: str,
    ) -> dict[str, Any]:
        """Utrwal YAML po jawnym zatwierdzeniu użytkownika na czacie."""
        state = ctx.deps.store.get(_conversation_id(ctx))
        if not state.pending_yaml or not state.pending_yaml_fingerprint:
            return {
                "accepted": False,
                "error": "Brak aktualnego YAML preview do zatwierdzenia.",
            }
        if contract_fingerprint != state.pending_yaml_fingerprint:
            return {
                "accepted": False,
                "error": (
                    "Fingerprint nie odpowiada aktualnemu YAML preview. "
                    "Wygeneruj preview ponownie."
                ),
            }
        state.last_valid_rendered_yaml = state.pending_yaml
        state.last_valid_yaml_fingerprint = state.pending_yaml_fingerprint
        ctx.deps.store.save(state)
        return {
            "accepted": True,
            "yaml": state.last_valid_rendered_yaml,
            "contractFingerprint": state.last_valid_yaml_fingerprint,
            "message": (
                "YAML został zatwierdzony. Dalsza poprawka utworzy nową "
                "rewizję, a ta wersja pozostanie jako last_valid_rendered_yaml."
            ),
        }


def _conversation_id(ctx: RunContext[Any]) -> str:
    return str(ctx.conversation_id or "local-default")
