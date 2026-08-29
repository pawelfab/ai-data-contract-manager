"""Measure the session audit size reduction on recorded JSONL sessions.

Replays the pre-change baselines in `ai-data-contract-manager/logs/sessions/` through the
real audit view functions, so the reported numbers come from the shipped mapping and not
from a hand-written approximation.

Run from the repository root:

    ai-data-contract-manager/.venv/Scripts/python.exe \
        docs/active-task/2026-08-29_compact-session-audit/measure_audit_size.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ai-data-contract-manager" / "src"))

from adcm.application.observability.audit_views import (  # noqa: E402
    _missing_view,
    forge_analysis_completed_view,
)
from adcm.domain.forge import ForgeAnalysis  # noqa: E402


def compact(event: dict) -> dict:
    data = event["data"]
    event_type = event["event_type"]

    if event_type == "forge.analysis.completed":
        context = {key: data.pop(key) for key in ("round", "contract_revision", "phase") if key in data}
        duration_ms = data.pop("duration_ms")
        analysis = ForgeAnalysis.model_validate(data)
        event["data"] = forge_analysis_completed_view(
            analysis,
            round_no=context["round"],
            contract_revision=context["contract_revision"],
            duration_ms=duration_ms,
            phase=context.get("phase"),
        )
    elif event_type == "turn.completed":
        report = data.get("stabilization", {})
        data["stabilization"] = {"rounds": report.get("rounds"), "converged": report.get("converged")}
        data["missing"] = [
            _missing_view(_MissingLike(item), "normal") for item in data.get("missing", [])
        ]
    return event


class _MissingLike:
    """Recorded missing requirements are plain dicts in the baseline files."""

    def __init__(self, item: dict) -> None:
        self.path = item["path"]
        self.code = item.get("code", "required")
        self.expected_type = item.get("expected_type")
        self.allowed_values = item.get("allowed_values")

    def model_dump(self, mode: str = "json") -> dict:
        return {
            "path": self.path,
            "code": self.code,
            "expected_type": self.expected_type,
            "allowed_values": self.allowed_values,
        }


def encode(event: dict) -> int:
    return len(json.dumps(event, ensure_ascii=False).encode("utf-8")) + 1


def payload(event: dict) -> int:
    return len(json.dumps(event["data"], ensure_ascii=False).encode("utf-8"))


def report(path: Path) -> None:
    before = after = before_payload = after_payload = 0
    remaining: Counter[str] = Counter()
    events = 0

    for line in path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        events += 1
        before += encode(event)
        before_payload += payload(event)
        event = compact(event)
        size = encode(event)
        after += size
        after_payload += payload(event)
        remaining[event["event_type"]] += size

    print(f"\n{path.name}: {events} events")
    print(f"  total   {before:>7} B -> {after:>7} B  ({100 * (before - after) / before:5.1f}% smaller)")
    print(
        f"  payload {before_payload:>7} B -> {after_payload:>7} B  "
        f"({100 * (before_payload - after_payload) / before_payload:5.1f}% smaller)"
    )
    print("  largest remaining event types:")
    for event_type, size in remaining.most_common(5):
        print(f"    {event_type:<32} {size:>7} B  ({100 * size / after:4.1f}%)")


if __name__ == "__main__":
    sessions = ROOT / "ai-data-contract-manager" / "logs" / "sessions"
    for jsonl in sorted(sessions.glob("*.jsonl")):
        report(jsonl)
