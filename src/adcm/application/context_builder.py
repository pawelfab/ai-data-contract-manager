from adcm.domain.models import AgentContext, ConversationState, PreferenceView, SignalView


class AgentContextBuilder:
    def build(self, state: ConversationState, *, recent_message_limit: int = 12) -> AgentContext:
        view = state.workflow.current_schema_view
        allowed = sorted(view.allowed_path_set) if view is not None else []
        return AgentContext(
            current_stage=state.workflow.current_stage,
            active_signals=[
                SignalView(id=s.id, concept=s.concept, value=s.value, status=s.status)
                for s in state.signals
                if s.status not in {"superseded", "rejected"}
            ],
            active_preferences=[
                PreferenceView(id=p.id, concept=p.concept, value=p.value, scope=p.scope)
                for p in state.preferences
                if p.active
            ],
            known_values={path: rv.value for path, rv in state.resolved_values.items()},
            allowed_paths=allowed,
            pending_requirements=state.workflow.pending_requirements,
            recent_messages=state.messages[-recent_message_limit:],
        )
