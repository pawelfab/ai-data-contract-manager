from __future__ import annotations

from typing import Any

from pydantic_ai.capabilities import ValidatedToolArgs

from .serialization import plain, short


def build_decision_trace(
    tool_name: str,
    args: ValidatedToolArgs,
    result: Any,
    user_text: str | None,
) -> dict[str, Any] | None:
    """Summarize observable decisions without inventing hidden reasoning."""

    plain_args = plain(args)
    plain_result = plain(result)
    if not isinstance(plain_args, dict):
        plain_args = {}
    if not isinstance(plain_result, dict):
        plain_result = {"value": plain_result}

    if tool_name == "configure_contract_scope":
        source_type = plain_result.get(
            "sourceType", plain_args.get("source_type")
        )
        layers = plain_result.get(
            "targetLayers", plain_args.get("target_layers") or ["bronze"]
        )
        basis = (
            f' na podstawie wypowiedzi użytkownika: "{short(user_text)}".'
            if user_text
            else "."
        )
        return {
            "decisionType": "contract_scope_selected",
            "summary": (
                f"Wybrano źródło {source_type!r} i warstwy {layers!r}"
                + basis
            ),
            "evidence": user_text,
            "details": {
                "sourceType": source_type,
                "targetLayers": layers,
            },
        }

    if tool_name == "apply_contract_patch":
        updates = plain_args.get("updates", [])
        paths = plain_result.get("changedPaths", [])
        return {
            "decisionType": "contract_patch_applied",
            "summary": "Zmieniono draft na ścieżkach: "
            + (", ".join(paths) if paths else "brak"),
            "evidence": [
                {
                    "path": update.get("path"),
                    "evidenceText": update.get("evidence_text"),
                }
                for update in updates
                if isinstance(update, dict)
            ],
            "details": {
                "origin": plain_args.get("origin", "user"),
                "changedPaths": paths,
                "updates": updates,
                "revision": plain_result.get("revision"),
            },
        }

    if tool_name == "set_optional_decisions":
        return {
            "decisionType": "optional_sections_selected",
            "summary": "Zapisano decyzje dotyczące sekcji opcjonalnych.",
            "evidence": user_text,
            "details": {
                "decisions": plain_args.get("decisions", []),
                "choices": plain_result.get("choices", {}),
            },
        }

    if tool_name == "validate_contract_draft":
        valid = plain_result.get("valid")
        if valid is True:
            summary = "Walidacja draftu przez MCP zakończyła się sukcesem."
        elif valid is False or plain_result.get("ok") is False:
            summary = "Walidacja draftu nie zakończyła się sukcesem."
        else:
            summary = "Wykonano próbę walidacji draftu przez MCP."
        return {
            "decisionType": "contract_validation_attempted",
            "summary": summary,
            "evidence": "Wynik walidacji zwrócony przez MCP.",
            "details": plain_result,
        }

    if tool_name == "prepare_yaml_preview":
        return {
            "decisionType": "yaml_preview_generated",
            "summary": "Wygenerowano YAML preview z poprawnego draftu.",
            "evidence": "Bieżący draft przeszedł walidację MCP.",
            "details": {
                "contractFingerprint": plain_result.get(
                    "contractFingerprint"
                )
            },
        }

    if tool_name == "approve_final_yaml":
        return {
            "decisionType": "yaml_approval_recorded",
            "summary": (
                "Zapisano zatwierdzenie końcowego YAML."
                if plain_result.get("accepted")
                else "Końcowy YAML nie został zatwierdzony."
            ),
            "evidence": user_text,
            "details": plain_result,
        }

    return None
