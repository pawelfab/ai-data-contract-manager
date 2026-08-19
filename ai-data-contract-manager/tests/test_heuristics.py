from adcm.heuristics import HeuristicResolver
from adcm.models import Requirement


DATA_TYPES = ["STRING", "INT64", "FLOAT64", "NUMERIC", "BOOLEAN", "DATE"]


def array_object_requirement(
    path: str = "source.columns",
    *,
    fixed_width: bool = False,
) -> Requirement:
    properties = {
        "name": {"type": "string"},
        "dataType": {"type": "string", "enum": DATA_TYPES},
        "nullable": {"type": "boolean"},
    }
    required = ["name", "dataType"]
    if fixed_width:
        properties.update(
            {
                "start": {"type": "integer"},
                "end": {"type": "integer"},
            }
        )
        required = ["name", "start", "end", "dataType"]
    return Requirement(
        path=path,
        question="items",
        value_schema={
            "type": "array",
            "items": {
                "type": "object",
                "required": required,
                "properties": properties,
            },
        },
    )


def test_source_system_typo():
    resolver = HeuristicResolver()
    requirement = Requirement(
        path="metadata.sourceSystemGcpId",
        question="system?",
        reason="source_system",
        value_schema={"type": "string", "enum": ["rocket", "sap"]},
        allowed_values=["rocket", "sap"],
    )
    out = resolver.extract(
        "roket",
        [requirement],
        {},
        allow_plain_fallback=True,
    )
    assert out == {"metadata.sourceSystemGcpId": "rocket"}


def test_parse_regular_columns():
    resolver = HeuristicResolver()
    requirement = array_object_requirement()
    out = resolver.extract(
        "account_id STRING NOT NULL\nbalance NUMERIC",
        [requirement],
        {},
        allow_plain_fallback=True,
    )
    assert out["source.columns"][0] == {
        "name": "account_id",
        "dataType": "STRING",
        "nullable": False,
    }
    assert out["source.columns"][1]["dataType"] == "NUMERIC"


def test_parse_fixed_width_columns():
    resolver = HeuristicResolver()
    requirement = array_object_requirement(fixed_width=True)
    out = resolver.extract(
        "account_id 0 8 STRING NOT NULL\nbalance 8 20 NUMERIC",
        [requirement],
        {},
        allow_plain_fallback=True,
    )
    assert out["source.columns"][0]["start"] == 0
    assert out["source.columns"][0]["end"] == 8
    assert out["source.columns"][0]["nullable"] is False


def test_json_array_and_case_insensitive_enums_are_normalized():
    resolver = HeuristicResolver()
    requirement = array_object_requirement()

    parsed = resolver.parse_structured(
        '[{"name": "data_d", "dataType": "date"}]',
        requirement,
    )

    assert parsed.complete is True
    assert parsed.value == [{"name": "data_d", "dataType": "DATE"}]


def test_invalid_datatype_is_partial_and_is_not_guessed():
    resolver = HeuristicResolver()
    requirement = array_object_requirement()

    parsed = resolver.parse_structured("data_d ORACLE_NUMBER", requirement)

    assert parsed.complete is False
    assert parsed.value == [{"name": "data_d"}]
    assert parsed.missing == ["dataType"]
    assert parsed.invalid == ["data_d.dataType=ORACLE_NUMBER"]


def test_array_object_parser_is_not_tied_to_source_columns_path():
    resolver = HeuristicResolver()
    requirement = array_object_requirement(path="custom.dataset.fields")

    parsed = resolver.parse_structured(
        "created_at date\ncustomer_id string",
        requirement,
    )

    assert parsed.complete is True
    assert parsed.value == [
        {"name": "created_at", "dataType": "DATE"},
        {"name": "customer_id", "dataType": "STRING"},
    ]


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
        "0 6 * * *",
        [cron],
        {},
        allow_plain_fallback=False,
    ) == {"orchestration.schedule": "0 6 * * *"}
    assert resolver.extract(
        "this ordinary sentence has five words",
        [cron],
        {},
        allow_plain_fallback=False,
    ) == {}
    assert resolver.extract(
        "rocket",
        [identifier],
        {},
        allow_plain_fallback=False,
    ) == {}
