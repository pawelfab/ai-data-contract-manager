from adcm.domain.turn import EffectiveIntentResolution, IntentKind, IntentResolution


class IntentResolutionPolicy:
    """Apply the deterministic boundary between resolver output and mutations."""

    def apply(self, resolution: IntentResolution) -> EffectiveIntentResolution:
        if resolution.intent_kind is IntentKind.KNOWLEDGE:
            candidates, knowledge_query = [], resolution.knowledge_query
        elif resolution.intent_kind is IntentKind.MUTATION:
            candidates, knowledge_query = list(resolution.candidates), None
        elif resolution.intent_kind is IntentKind.MIXED:
            candidates, knowledge_query = list(resolution.candidates), resolution.knowledge_query
        else:
            candidates, knowledge_query = [], None
        return EffectiveIntentResolution(
            intent_kind=resolution.intent_kind,
            candidates=candidates,
            knowledge_query=knowledge_query,
            unresolved=list(resolution.unresolved),
        )
