"""The scripted „robimy zasilanie" conversation, as data.

Deliberately free of pytest imports so the same script can be replayed by any runner.

Two tiers of expectation:

* hard — contract state and the Forge requirement sequence. Deterministic given correct
  extraction, so a mismatch is a real regression.
* soft — question wording and advisory warnings. Those come purely from LLM judgement
  (`_CONSISTENCY_INSTRUCTIONS` / `_QUESTION_INSTRUCTIONS`), so they are reported, not enforced,
  unless ADCM_LIVE_STRICT=1.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

Matcher = Callable[[Any], bool]


# --- matchers -------------------------------------------------------------------------------


def exact(expected: Any) -> Matcher:
    matcher: Matcher = lambda actual: actual == expected
    matcher.describe = f"== {expected!r}"  # type: ignore[attr-defined]
    return matcher


def icase(expected: str) -> Matcher:
    """Case-insensitive string match — the contract does not pin `utf-8` vs `UTF-8`."""

    matcher: Matcher = lambda actual: isinstance(actual, str) and actual.casefold() == expected.casefold()
    matcher.describe = f"~= {expected!r} (case-insensitive)"  # type: ignore[attr-defined]
    return matcher


def any_of(*expected: Any) -> Matcher:
    matcher: Matcher = lambda actual: actual in expected
    matcher.describe = f"in {list(expected)!r}"  # type: ignore[attr-defined]
    return matcher


def is_true() -> Matcher:
    matcher: Matcher = lambda actual: actual is True
    matcher.describe = "is True"  # type: ignore[attr-defined]
    return matcher


def describe(matcher: Matcher) -> str:
    return getattr(matcher, "describe", repr(matcher))


# --- scenario model -------------------------------------------------------------------------


@dataclass
class Turn:
    user: str
    #: JSON pointer -> matcher. Hard.
    expect_document: dict[str, Matcher] = field(default_factory=dict)
    #: Exact set of requirement paths Forge must expose on the last round. Hard.
    expect_requirements: set[str] | None = None
    #: The composed question must contain at least one of these (case-insensitive). Soft.
    expect_question_mentions: tuple[str, ...] = ()
    #: A warning whose message matches this pattern is expected. Soft.
    expect_warning_like: str | None = None
    #: Notes carried into the transcript artifact.
    note: str = ""


#: Reproduces the manual session turn for turn. It stops where the manual transcript stops:
#: SAP switches `preparator.enabled` on, and the contract rule
#: `preparator.enabled_requires_operation` then blocks `valid=true` until an operation is given.
#: That is a documented, deliberate limitation, so the script never asserts final validity.
SCENARIO: list[Turn] = [
    Turn(
        user="robimy zasilanie",
        expect_document={},
        expect_requirements={"/metadata/sourceSystemGcpId"},
        expect_question_mentions=("system źródłowy", "sourcesystemgcpid", "system"),
        note="Nothing is extractable yet; Forge opens with the source-system anchor.",
    ),
    Turn(
        user="system sap",
        expect_document={
            "/metadata/sourceSystemGcpId": exact("sap"),
            "/metadata/id": exact("sap"),
        },
        expect_requirements={"/metadata/version", "/metadata/dataFileId"},
        expect_question_mentions=("wersja", "version", "datafileid", "data file"),
        note="global.source_system.metadata_id derives /metadata/id, so it drops out of the asks.",
    ),
    Turn(
        user="version 1.0.1, nazwa sap_pipeline",
        expect_document={
            "/metadata/version": exact("1.0.1"),
            "/metadata/dataFileId": exact("sap_pipeline"),
        },
        expect_requirements={"/orchestration/schedule", "/orchestration/startDate"},
        expect_question_mentions=("harmonogram", "schedule", "data startu", "startdate"),
    ),
    Turn(
        user="uruchomienie @daily, star date 2025-01-01",
        expect_document={
            "/orchestration/schedule": exact("@daily"),
            "/orchestration/startDate": exact("2025-01-01"),
        },
        expect_requirements={"/source/sourceType"},
        expect_question_mentions=("typ źródła", "sourcetype", "jdbc", "txt"),
        expect_warning_like=r"star\s*date|literów|typo",
        note="'star date' is a typo the LLM should read as 'start date' and flag, not silently fix.",
    ),
    Turn(
        user="typ plik txt",
        expect_document={
            "/source/sourceType": exact("txt"),
            "/source/systemZrodlowy": exact("sap"),
            "/converter/enabled": is_true(),
            "/preparator/enabled": is_true(),
        },
        expect_requirements={"/source/dataDanych", "/source/encoding"},
        expect_question_mentions=("datadanych", "data date", "encoding", "kodowanie"),
        note="SAP enrichment activates converter and preparator; txt branch requires encoding.",
    ),
    Turn(
        user="zmienna {date}, encoding utf-8",
        expect_document={
            "/source/dataDanych": exact("{date}"),
            "/source/encoding": icase("utf-8"),
            "/bronzeTable/table/project": exact("sap_bronze"),
            "/bronzeTable/table/dataset": exact("sap_bronze"),
            "/bronzeTable/table/table": exact("sap_bronze"),
            "/bronzeTable/columns": exact([]),
            "/silver/enabled": is_true(),
            "/silver/tables/0/table/project": exact("sap_silver"),
            "/silver/tables/0/table/dataset": exact("sap_silver"),
            "/silver/tables/0/table/table": exact("sap_silver"),
            "/silver/tables/0/source": exact("sap_bronze"),
            "/gold/enabled": is_true(),
            "/gold/entries/0/table/project": exact("sap_gold"),
            "/gold/entries/0/table/dataset": exact("sap_gold"),
            "/gold/entries/0/table/table": exact("sap_gold"),
        },
        expect_requirements={"/silver/tables/0/pk", "/silver/tables/0/columns"},
        expect_question_mentions=("pk", "columns", "kolumn", "silver"),
        expect_warning_like=r"startdate|start date|wstecz|backfill|2025-01-01",
        note=(
            "Source is complete, so bronze is scaffolded and filled, which in turn unlocks "
            "silver and gold. pk/columns stay user questions by design."
        ),
    ),
]


#: Failure signatures that correspond to already-known, deliberately out-of-scope defects.
#: Annotating them keeps a red run readable: a known defect must not look like a fresh
#: regression. They still fail the test — this only explains *why*.
KNOWN_ISSUES: list[tuple[str, str]] = [
    (
        r"/metadata/dataFileId",
        "ZNANY DEFEKT: LLM wnioskuje /metadata/dataFileId z nazwy systemu ('system sap' -> "
        "dataFileId='sap'). Wymaganie znika, więc podana później nazwa nie ma już gdzie trafić. "
        "Wymienione jako poza zakresem w docs/active-tasks/"
        "2026-08-23-source-bronze-silver-gold-flow/PLAN.md.",
    ),
]


def known_issue(failure: str) -> str | None:
    """Return the explanation if this failure is an already-known defect, else None."""

    for pattern, explanation in KNOWN_ISSUES:
        if re.search(pattern, failure):
            return explanation
    return None


def matches_warning(warnings: list[Any], pattern: str) -> bool:
    regex = re.compile(pattern, re.IGNORECASE)
    return any(regex.search(getattr(w, "message", "") or "") for w in warnings)


def question_mentions(question: str | None, keywords: tuple[str, ...]) -> bool:
    if not question or not keywords:
        return bool(question)
    lowered = question.casefold()
    return any(keyword.casefold() in lowered for keyword in keywords)
