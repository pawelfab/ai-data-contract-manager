from adcm.domain.contract_path import ContractPath
from adcm.domain.models import AllowedPath, CandidateScope, Signal, ValueCandidate


class SignalBinder:
    """Binds schema-agnostic user signals only to paths authorized by Forge."""

    def bind(self, signals: list[Signal], allowed_paths: list[AllowedPath]) -> list[ValueCandidate]:
        by_concept: dict[str, list[AllowedPath]] = {}
        for allowed in allowed_paths:
            try:
                ContractPath.parse(allowed.path)
            except ValueError:
                continue
            for concept in allowed.concepts:
                by_concept.setdefault(concept, []).append(allowed)

        candidates: list[ValueCandidate] = []
        for signal in signals:
            if signal.status in {"superseded", "rejected"}:
                continue
            matches = by_concept.get(signal.concept, [])
            if len(matches) != 1:
                signal.status = "unbound"
                continue
            allowed = matches[0]
            candidates.append(
                ValueCandidate(
                    path=allowed.path,
                    value=signal.value,
                    origin=signal.origin,
                    evidence_ids=list(signal.evidence_ids),
                    confidence=signal.confidence,
                    scope=CandidateScope.USER,
                    source_signal_id=signal.id,
                    created_revision=signal.created_revision,
                    reason=f"bound from signal:{signal.concept}",
                )
            )
            signal.status = "bound"
        return candidates
