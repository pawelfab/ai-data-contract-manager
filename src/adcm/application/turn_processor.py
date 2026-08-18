from adcm.domain.models import (
    ChatMessage,
    ConversationState,
    Evidence,
    EvidenceKind,
    Preference,
    Revision,
    Signal,
    TurnInterpretation,
    ValueChange,
    ValueOrigin,
)


class TurnProcessor:
    """Applies semantic interpretation to ADCM knowledge state; never writes ContractDraft."""

    def apply_user_turn(
        self,
        state: ConversationState,
        message: ChatMessage,
        interpretation: TurnInterpretation,
    ) -> None:
        state.messages.append(message)
        evidence = Evidence(
            kind=EvidenceKind.USER_MESSAGE,
            source_id=str(message.id),
            content=message.content,
            message_id=message.id,
        )
        state.evidence.append(evidence)
        changes: list[ValueChange] = []
        next_revision = state.revision + 1

        for correction in interpretation.corrections:
            if correction.intent == "uncertain":
                continue
            superseded_signal_id = None
            for signal in reversed(state.signals):
                if signal.concept == correction.concept and signal.status not in {"superseded", "rejected"}:
                    old = signal.value
                    signal.status = "superseded"
                    superseded_signal_id = signal.id
                    changes.append(
                        ValueChange(
                            concept=correction.concept,
                            old=old,
                            new=correction.new_value,
                            reason="user_correction",
                        )
                    )
                    break
            if superseded_signal_id is not None:
                for candidate in state.value_candidates:
                    if candidate.source_signal_id == superseded_signal_id:
                        candidate.status = "superseded"
            state.signals.append(
                Signal(
                    concept=correction.concept,
                    value=correction.new_value,
                    origin=ValueOrigin.USER_EXPLICIT,
                    evidence_ids=[evidence.id],
                    confidence=1.0,
                    created_revision=next_revision,
                )
            )

        for extracted in interpretation.extracted_signals:
            duplicate = any(
                s.concept == extracted.concept
                and s.value == extracted.value
                and s.status not in {"superseded", "rejected"}
                for s in state.signals
            )
            if duplicate:
                continue
            state.signals.append(
                Signal(
                    concept=extracted.concept,
                    value=extracted.value,
                    origin=ValueOrigin.USER_EXPLICIT,
                    scope=extracted.scope,
                    evidence_ids=[evidence.id],
                    confidence=extracted.confidence,
                    created_revision=next_revision,
                )
            )
            changes.append(ValueChange(concept=extracted.concept, new=extracted.value, reason="user_signal"))

        for pref in interpretation.preferences:
            for previous in state.preferences:
                if previous.concept == pref.concept and previous.active and previous.value != pref.value:
                    previous.active = False
                    for candidate in state.value_candidates:
                        if candidate.source_preference_id == previous.id:
                            candidate.status = "superseded"
            duplicate = any(p.concept == pref.concept and p.value == pref.value and p.active for p in state.preferences)
            if not duplicate:
                state.preferences.append(
                    Preference(
                        concept=pref.concept,
                        value=pref.value,
                        origin=ValueOrigin.USER_PREFERENCE,
                        scope=pref.scope,
                        evidence_ids=[evidence.id],
                        created_revision=next_revision,
                    )
                )
                changes.append(ValueChange(concept=pref.concept, new=pref.value, reason="user_preference"))

        if changes:
            state.revision = next_revision
            state.revisions.append(
                Revision(revision=state.revision, changes=changes, trigger_message_id=message.id)
            )
