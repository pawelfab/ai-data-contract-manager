import math
from collections import defaultdict

from adcm.domain.models import DEFAULT_ORIGIN_PRIORITY, ResolvedValue, ValueCandidate


class CandidateResolver:
    """Deterministic precedence. The LLM never selects the winning value."""

    @staticmethod
    def _preflight(candidates: list[ValueCandidate]) -> None:
        seen_ids = set()
        for candidate in candidates:
            if candidate.id in seen_ids:
                raise ValueError(f"Duplicate candidate ID: {candidate.id}")
            seen_ids.add(candidate.id)
            confidence = candidate.confidence
            if confidence is not None and not math.isfinite(confidence):
                raise ValueError(f"Candidate {candidate.id} has non-finite confidence")

    @staticmethod
    def _rank(candidate: ValueCandidate) -> tuple[int, int, int, int, float]:
        # ADCM origin precedence applies before Forge rule priority. Forge priority
        # only distinguishes candidates with the same origin. Revision and sequence
        # resolve corrections; confidence is the explicit final policy tie-break.
        confidence = candidate.confidence
        return (
            DEFAULT_ORIGIN_PRIORITY[candidate.origin],
            candidate.priority if candidate.priority is not None else 0,
            candidate.created_revision,
            candidate.sequence,
            confidence if confidence is not None else 0.0,
        )

    def resolve(self, candidates: list[ValueCandidate]) -> dict[str, ResolvedValue]:
        self._preflight(candidates)

        by_path: dict[str, list[ValueCandidate]] = defaultdict(list)
        for candidate in candidates:
            if candidate.status not in {"rejected", "superseded"}:
                by_path[candidate.path].append(candidate)

        winners: dict[str, ValueCandidate] = {}
        for path, path_candidates in by_path.items():
            ranked = sorted(path_candidates, key=self._rank, reverse=True)
            winner = ranked[0]
            if (
                len(ranked) > 1
                and self._rank(winner) == self._rank(ranked[1])
            ):
                raise ValueError(
                    f"Ambiguous candidate rank for {path!r}; "
                    "priority, revision, sequence, or confidence must distinguish candidates"
                )
            winners[path] = winner

        resolved = {
            path: ResolvedValue(
                path=path,
                value=winner.value,
                selected_candidate_id=winner.id,
                origin=winner.origin,
                evidence_ids=winner.evidence_ids,
            )
            for path, winner in winners.items()
        }

        for path, path_candidates in by_path.items():
            winner = winners[path]
            for candidate in path_candidates:
                candidate.status = "selected" if candidate is winner else "candidate"
        return resolved
