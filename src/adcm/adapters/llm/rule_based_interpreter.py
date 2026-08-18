"""Tiny deterministic interpreter used only for demo/tests, never as production semantics."""

import unicodedata

from adcm.domain.models import AgentContext, ExtractedPreference, ExtractedSignal, TurnInterpretation


def _ascii_fold(text: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))


class RuleBasedInterpreter:
    async def interpret_turn(self, text: str, context: AgentContext) -> TurnInterpretation:
        lower = text.lower()
        folded = _ascii_fold(lower)
        signals = []
        preferences = []

        for token in ["sap", "oracle", "postgresql", "crm2", "unknown-system"]:
            if token in lower:
                signals.append(ExtractedSignal(concept="source_system", value=token.upper()))
                break
        if "csv" in lower:
            signals.append(ExtractedSignal(concept="source_format", value="csv"))
        if ";" in text or "srednik" in folded:
            signals.append(ExtractedSignal(concept="field_delimiter", value=";"))
        if "utf-8" in lower or "utf8" in lower:
            preferences.append(ExtractedPreference(concept="encoding", value="UTF-8"))
        if "bez szyfrowania" in lower or "nie uzywamy szyfrowania" in folded:
            preferences.append(ExtractedPreference(concept="encryption", value=False))

        marker = "id="
        if marker in lower:
            value = text[lower.index(marker) + len(marker) :].split()[0].strip(",.;")
            signals.append(ExtractedSignal(concept="feed_name", value=value))

        return TurnInterpretation(extracted_signals=signals, preferences=preferences)
