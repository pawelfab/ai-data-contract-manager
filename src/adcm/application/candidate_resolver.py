from collections import defaultdict

from adcm.domain.models import ResolvedValue, ValueCandidate


class CandidateResolver:
    """Deterministic precedence. The LLM never selects the winning value."""

    @staticmethod
    def _rank(candidate: ValueCandidate) -> tuple[int, int, int, float]:
        # Explicit priority is supplied by Forge for conflicts between Forge rules.
        # created_revision/sequence deterministically resolve same-origin corrections.
        return (
            candidate.effective_priority(),
            candidate.created_revision,
            candidate.sequence,
            candidate.confidence or 0.0,
        )

    def resolve(self, candidates: list[ValueCandidate]) -> dict[str, ResolvedValue]:
        by_path: dict[str, list[ValueCandidate]] = defaultdict(list)
        for candidate in candidates:
            if candidate.status not in {"rejected", "superseded"}:
                by_path[candidate.path].append(candidate)

        resolved: dict[str, ResolvedValue] = {}
        for path, path_candidates in by_path.items():
            winner = max(path_candidates, key=self._rank)
            for candidate in path_candidates:
                candidate.status = "selected" if candidate.id == winner.id else "candidate"
            resolved[path] = ResolvedValue(
                path=path,
                value=winner.value,
                selected_candidate_id=winner.id,
                origin=winner.origin,
                evidence_ids=winner.evidence_ids,
            )
        return resolved
