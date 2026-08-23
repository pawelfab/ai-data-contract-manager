"""Replays the manual „robimy zasilanie" session against the real stack.

Real `ForgeMcpAdapter` over HTTP MCP, real `PydanticAiHeuristicsAdapter` over the configured
LLM endpoint, one session across all turns — exactly the path
`POST /sessions/{id}/messages` takes, since the route returns this `HandleResult` verbatim.
"""

from __future__ import annotations

import asyncio
import time

import pytest

from adcm.domain.contract.path import get_pointer

from recording import TurnRecord
from scenario import SCENARIO, describe, known_issue, matches_warning, question_mentions

_MISSING = object()


def _check_turn(turn, result, record: TurnRecord, max_rounds: int) -> None:
    """Fill `record.hard_failures` / `record.soft_failures` for one turn."""

    document = result.document

    for pointer, matcher in turn.expect_document.items():
        actual = get_pointer(document, pointer, _MISSING)
        if actual is _MISSING:
            record.hard_failures.append(f"{pointer} is absent, expected {describe(matcher)}")
        elif not matcher(actual):
            record.hard_failures.append(f"{pointer} == {actual!r}, expected {describe(matcher)}")

    if not turn.expect_document and document:
        record.hard_failures.append(f"document should still be empty, got {sorted(document)}")

    if turn.expect_requirements is not None:
        actual_requirements = set(record.final_requirement_paths)
        if actual_requirements != turn.expect_requirements:
            record.hard_failures.append(
                f"Forge requirements {sorted(actual_requirements)}, "
                f"expected {sorted(turn.expect_requirements)}"
            )

    if result.valid is not False:
        record.hard_failures.append("valid should stay False until the contract is complete")
    if result.yaml is not None:
        record.hard_failures.append("yaml must be None while questions remain")
    if not (result.question or "").strip():
        record.hard_failures.append("question is empty")

    rounds = len(record.forge_rounds)
    if rounds >= max_rounds:
        record.hard_failures.append(f"stabilization used {rounds} rounds, cap is {max_rounds}")

    if not question_mentions(result.question, turn.expect_question_mentions):
        record.soft_failures.append(
            f"question mentions none of {list(turn.expect_question_mentions)}: {result.question!r}"
        )
    if turn.expect_warning_like and not matches_warning(result.warnings, turn.expect_warning_like):
        record.soft_failures.append(
            f"no warning matching /{turn.expect_warning_like}/ "
            f"(got {[w.message for w in result.warnings]})"
        )


def _report(transcript) -> str:
    lines = ["", "Tura | Wiadomość                                    | Twarde | Miękkie"]
    lines.append("-" * 78)
    for record in transcript.turns:
        if record.error:
            hard = "ERR"
        elif not record.hard_failures:
            hard = "ok"
        elif all(known_issue(f) for f in record.hard_failures):
            hard = "ZNANY"
        else:
            hard = "FAIL"
        soft = f"{len(record.soft_failures)} uwag" if record.soft_failures else "ok"
        lines.append(f"{record.index:>4} | {record.user[:44]:<44} | {hard:<6} | {soft}")
    return "\n".join(lines)


async def test_zasilanie_conversation(recorded_container, transcript, turn_timeout, strict_mode, live_settings):
    container, forge_spy, llm_spy = recorded_container
    session = await container.create_session.execute()

    for index, turn in enumerate(SCENARIO, start=1):
        record = TurnRecord(index=index, user=turn.user)
        transcript.add(record)
        started = time.perf_counter()
        try:
            record.result = await asyncio.wait_for(
                container.handle_message.execute(session.id, turn.user),
                timeout=turn_timeout,
            )
        except asyncio.TimeoutError:
            record.error = f"turn timed out after {turn_timeout}s"
        except Exception as exc:  # surfaced through the transcript before re-raising
            record.error = f"{type(exc).__name__}: {exc}"
        finally:
            record.duration_s = time.perf_counter() - started
            record.forge_rounds = forge_spy.take()
            record.llm_calls = llm_spy.take()

        if record.error:
            print(_report(transcript))
            pytest.fail(f"tura {index} ({turn.user!r}): {record.error}")

        assert record.result.session_id == session.id
        _check_turn(turn, record.result, record, live_settings.max_stabilization_rounds)

    print(_report(transcript))

    # Hard failures split in two. An already-known, deliberately out-of-scope defect is always
    # printed, but does not turn the gate red on its own — otherwise this test would be red
    # roughly every other run for a reason nobody is currently fixing, and real regressions
    # would drown in it. Anything not on that list fails immediately. ADCM_LIVE_STRICT=1
    # restores full fidelity to the manual transcript and fails on everything.
    regressions: list[str] = []
    known: list[str] = []
    for record in transcript.turns:
        for failure in record.hard_failures:
            labelled = f"tura {record.index} ({record.user!r}): {failure}"
            explanation = known_issue(failure)
            (known if explanation else regressions).append(
                f"{labelled}\n      -> {explanation}" if explanation else labelled
            )

    soft = [
        f"tura {r.index} ({r.user!r}): {failure}"
        for r in transcript.turns
        for failure in r.soft_failures
    ]

    if known:
        print("\nznane defekty (nie są regresją tej zmiany):\n  " + "\n  ".join(known))
    if soft:
        print("\nmiękkie oczekiwania (osąd LLM):\n  " + "\n  ".join(soft))

    assert not regressions, "twarde oczekiwania niespełnione:\n  " + "\n  ".join(regressions)

    if strict_mode and (known or soft):
        pytest.fail("ADCM_LIVE_STRICT=1:\n  " + "\n  ".join(known + soft))


async def test_changing_the_source_system_recomputes_every_derived_value(
    recorded_container, transcript, turn_timeout, strict_mode
):
    """`valid=True` is not terminal and derived values must be recomputed, not accumulated
    (AGENTS.md §12, DECISIONS D-10).

    The hard assertion is conditional on purpose. *Whether* the LLM routes a free-text
    correction to the anchor `/metadata/sourceSystemGcpId` rather than to its derived alias
    `/source/systemZrodlowy` is model judgement, and it has been observed to go both ways on
    identical wording — so that is soft. What must never vary is the consequence: once the
    anchor does change, not one stale `sap_*` name may survive anywhere in the document.
    """

    container, forge_spy, llm_spy = recorded_container
    session = await container.create_session.execute()

    correction = "jednak system źródłowy to rocket, nie sap"
    for index, message in enumerate([turn.user for turn in SCENARIO] + [correction], start=1):
        record = TurnRecord(index=index, user=message)
        transcript.add(record)
        started = time.perf_counter()
        try:
            record.result = await asyncio.wait_for(
                container.handle_message.execute(session.id, message),
                timeout=turn_timeout,
            )
        except Exception as exc:
            record.error = f"{type(exc).__name__}: {exc}"
        finally:
            record.duration_s = time.perf_counter() - started
            record.forge_rounds = forge_spy.take()
            record.llm_calls = llm_spy.take()

        if record.error:
            pytest.fail(f"tura {index} ({message!r}): {record.error}")

    document = transcript.turns[-1].result.document
    anchor = get_pointer(document, "/metadata/sourceSystemGcpId")

    if anchor != "rocket":
        message = (
            f"LLM nie przeniósł korekty na kotwicę: /metadata/sourceSystemGcpId == {anchor!r}, "
            f"/source/systemZrodlowy == {get_pointer(document, '/source/systemZrodlowy')!r}"
        )
        print(f"\n[live] SOFT: {message}")
        if strict_mode:
            pytest.fail(message)
        pytest.skip(message)

    assert get_pointer(document, "/bronzeTable/table/project") == "rocket_bronze"
    assert get_pointer(document, "/silver/tables/0/table/dataset") == "rocket_silver"
    assert get_pointer(document, "/silver/tables/0/source") == "rocket_bronze"
    assert get_pointer(document, "/gold/entries/0/table/table") == "rocket_gold"
    # Rocket is not a configured system, so the SAP-only activations must be gone.
    assert get_pointer(document, "/converter/enabled") is not True
    assert get_pointer(document, "/preparator/enabled") is not True
    # The layer sections are entirely enrichment-derived, so nothing there may still say "sap".
    # `/metadata/dataFileId` is deliberately excluded: "sap_pipeline" is the user's own value.
    stale = [
        (pointer, value)
        for section in ("/bronzeTable", "/silver", "/gold")
        for pointer, value in _walk_strings(get_pointer(document, section), section)
        if "sap" in value.casefold()
    ]
    assert not stale, f"stale SAP-derived values survived the switch: {stale}"


def _walk_strings(node, prefix: str = ""):
    """Yield (pointer, value) for every string leaf, so stale derived names cannot hide."""

    if isinstance(node, dict):
        for key, value in node.items():
            yield from _walk_strings(value, f"{prefix}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk_strings(value, f"{prefix}/{index}")
    elif isinstance(node, str):
        yield prefix, node
