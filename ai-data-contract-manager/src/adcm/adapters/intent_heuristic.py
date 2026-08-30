import json
import re

from adcm.domain.forge import ForgeDescription
from adcm.domain.mutations import CandidateAction, MutationCandidate
from adcm.domain.turn import IntentKind, IntentResolution


_ASSIGNMENT = re.compile(r"^(?:set\s+|ustaw\s+|zmień\s+|zmien\s+)?(?P<path>/\S+)\s*=\s*(?P<value>.+)$", re.I)
_REMOVE = re.compile(r"^(?:remove|delete|usuń|usun)\s+(?P<path>/\S+)\s*$", re.I)
_SYSTEM = re.compile(r"^(?:system|system\s+źródłowy|system\s+zrodlowy)\s+(?P<value>[\w.-]+)\s*$", re.I)


_KNOWLEDGE = re.compile(
    r"(?:jakie|jaki|jak|co)\b.*"
    r"(?:opcje|pola|typy|wartości|wartosci|dostępne|dostepne|uzupełnić|uzupelnic)",
    re.I,
)


class HeuristicIntentResolver:
    """Deterministic bootstrap adapter. It is intentionally small, not the final language layer."""

    async def resolve(
        self,
        message: str,
        *,
        document: dict,
        definition: ForgeDescription | None = None,
    ) -> IntentResolution:
        text = message.strip()
        if match := _REMOVE.match(text):
            return IntentResolution(
                intent_kind=IntentKind.MUTATION,
                candidates=[
                    MutationCandidate(
                        action=CandidateAction.REMOVE,
                        path=match.group("path"),
                        evidence=text,
                    )
                ],
            )
        if match := _ASSIGNMENT.match(text):
            return IntentResolution(
                intent_kind=IntentKind.MUTATION,
                candidates=[
                    MutationCandidate(
                        action=CandidateAction.SET,
                        path=match.group("path"),
                        value=self._parse_value(match.group("value")),
                        evidence=text,
                    )
                ]
            )
        if match := _SYSTEM.match(text):
            return IntentResolution(
                intent_kind=IntentKind.MUTATION,
                candidates=[
                    MutationCandidate(
                        action=CandidateAction.SET,
                        path="/metadata/sourceSystemGcpId",
                        value=match.group("value"),
                        evidence=text,
                    )
                ]
            )
        if _KNOWLEDGE.search(text):
            return IntentResolution(intent_kind=IntentKind.KNOWLEDGE, knowledge_query=text)
        return IntentResolution(
            intent_kind=IntentKind.UNRESOLVED,
            unresolved=[{"value": text, "reason": "intent not recognized"}],
        )

    @staticmethod
    def _parse_value(raw: str):
        raw = raw.strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw.strip('"\'')
