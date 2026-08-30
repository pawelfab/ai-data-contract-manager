import yaml

from adcm.domain.turn import IntentKind, TurnOutcome


class BasicResponseComposer:
    async def compose(self, outcome: TurnOutcome) -> str:
        if outcome.intent_kind is IntentKind.UNRESOLVED:
            return (
                "Nie udało mi się jednoznacznie zrozumieć Twojej wypowiedzi. "
                "Proszę, doprecyzuj, co chcesz osiągnąć."
            )
        status = outcome.forge.status
        parts = [f"valid={status.valid}, complete={status.complete}, clean={status.clean}"]
        if not outcome.stabilization.converged:
            parts.append("stabilizacja nie osiągnęła fixed point")
        if outcome.stabilization.foreign_removed:
            parts.append("usunięto pola obce: " + ", ".join(outcome.stabilization.foreign_removed))
        if outcome.forge.diagnostics:
            parts.append("błędy: " + "; ".join(item.message for item in outcome.forge.diagnostics))
        if outcome.forge.missing:
            parts.append("brak: " + ", ".join(item.path for item in outcome.forge.missing))
        if status.valid and status.complete:
            parts.append("YAML:\n" + yaml.safe_dump(outcome.document, allow_unicode=True, sort_keys=False))
        return "\n".join(parts)
