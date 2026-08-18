from adcm.domain.models import AllowedPath, Signal, ValueCandidate, ValueOrigin


class SignalBinder:
    """Binds schema-agnostic concepts only to paths already authorized by MCP."""

    def bind(self, signals: list[Signal], allowed_paths: list[AllowedPath]) -> list[ValueCandidate]:
        by_concept: dict[str, list[AllowedPath]] = {}
        for allowed in allowed_paths:
            for concept in allowed.concepts:
                by_concept.setdefault(concept, []).append(allowed)

        candidates: list[ValueCandidate] = []
        for signal in signals:
            if signal.status in {"superseded", "rejected"}:
                continue
            matches = by_concept.get(signal.concept, [])
            if len(matches) != 1:
                continue
            path = matches[0].path
            candidates.append(
                ValueCandidate(
                    path=path,
                    value=signal.value,
                    origin=ValueOrigin.USER_EXPLICIT,
                    evidence_ids=signal.evidence_ids,
                    confidence=signal.confidence,
                    reason=f"bound from signal:{signal.concept}",
                )
            )
            signal.status = "bound"
        return candidates
