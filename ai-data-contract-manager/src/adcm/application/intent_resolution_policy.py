from adcm.domain.turn import EffectiveIntentResolution, IntentKind, IntentResolution


class IntentResolutionPolicy:
    """Apply the deterministic boundary between resolver output and mutations."""

    _KNOWLEDGE_QUERY_REQUIRED = "knowledge_query is required for this intent kind"
    _UNRESOLVED_REASON = "intent could not be resolved"

    def apply(self, resolution: IntentResolution) -> EffectiveIntentResolution:
        unresolved = list(resolution.unresolved)
        kind = resolution.intent_kind
        query = resolution.knowledge_query.strip() if resolution.knowledge_query else None
        if kind is IntentKind.MUTATION:
            candidates, knowledge_query = list(resolution.candidates), None
        elif kind in (IntentKind.KNOWLEDGE, IntentKind.MIXED):
            if not query:
                return self._unresolved(unresolved, self._KNOWLEDGE_QUERY_REQUIRED)
            candidates, knowledge_query = ([] if kind is IntentKind.KNOWLEDGE else list(resolution.candidates)), query
        else:
            candidates, knowledge_query = [], None
            if not any(self._has_reason(item) for item in unresolved):
                unresolved.append({"reason": self._UNRESOLVED_REASON})
        return EffectiveIntentResolution(
            intent_kind=kind,
            candidates=candidates,
            knowledge_query=knowledge_query,
            unresolved=unresolved,
        )

    def _unresolved(self, unresolved: list[dict], reason: str) -> EffectiveIntentResolution:
        unresolved.append({"reason": reason})
        return EffectiveIntentResolution(
            intent_kind=IntentKind.UNRESOLVED,
            candidates=[],
            knowledge_query=None,
            unresolved=unresolved,
        )

    @staticmethod
    def _has_reason(item: dict) -> bool:
        reason = item.get("reason")
        return isinstance(reason, str) and bool(reason.strip())
