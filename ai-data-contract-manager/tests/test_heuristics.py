from adcm.heuristics import HeuristicResolver
from adcm.models import Requirement


def test_source_system_typo():
    r = HeuristicResolver()
    req = Requirement(
        path="metadata.sourceSystemGcpId",
        question="system?",
        reason="source_system",
        value_schema={"type": "string", "enum": ["rocket", "sap"]},
        allowed_values=["rocket", "sap"],
    )
    out = r.extract("roket", [req], {}, allow_plain_fallback=True)
    assert out == {"metadata.sourceSystemGcpId": "rocket"}


def test_parse_regular_columns():
    r = HeuristicResolver()
    req = Requirement(path="source.columns", question="columns", value_schema={"type": "array"})
    out = r.extract(
        "account_id STRING NOT NULL\nbalance NUMERIC",
        [req],
        {"source": {"sourceType": "csv"}},
        allow_plain_fallback=True,
    )
    assert out["source.columns"][0] == {"name": "account_id", "dataType": "STRING", "nullable": False}
    assert out["source.columns"][1]["dataType"] == "NUMERIC"


def test_parse_fixed_width_columns():
    r = HeuristicResolver()
    req = Requirement(path="source.columns", question="columns", value_schema={"type": "array"})
    out = r.extract(
        "account_id 0 8 STRING NOT NULL\nbalance 8 20 NUMERIC",
        [req],
        {"source": {"sourceType": "fixed_width"}},
        allow_plain_fallback=True,
    )
    assert out["source.columns"][0]["start"] == 0
    assert out["source.columns"][0]["end"] == 8
    assert out["source.columns"][0]["nullable"] is False


def test_strict_history_accepts_unambiguous_cron_but_not_generic_pattern_matches():
    resolver = HeuristicResolver()
    cron = Requirement(
        path="orchestration.schedule",
        question="schedule",
        value_schema={
            "type": "string",
            "pattern": r"^\S+(?:\s+\S+){4}$",
            "description": "Harmonogram w formacie Linux cron.",
        },
    )
    identifier = Requirement(
        path="metadata.id",
        question="id",
        value_schema={"type": "string", "pattern": "^[a-z][a-z0-9_-]*$"},
    )

    assert resolver.extract(
        "0 6 * * *", [cron], {}, allow_plain_fallback=False
    ) == {"orchestration.schedule": "0 6 * * *"}
    assert resolver.extract(
        "this ordinary sentence has five words",
        [cron],
        {},
        allow_plain_fallback=False,
    ) == {}
    assert resolver.extract(
        "rocket", [identifier], {}, allow_plain_fallback=False
    ) == {}
