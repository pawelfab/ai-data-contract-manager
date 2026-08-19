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
        allow_plain_fallback=True,
    )
    assert out == {"metadata.sourceSystemGcpId": "rocket"}


def test_parse_regular_columns():
    resolver = HeuristicResolver()
    requirement = array_object_requirement()
    out = resolver.extract(
        "account_id STRING NOT NULL\nbalance NUMERIC",
        [requirement],
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
        allow_plain_fallback=False,
    ) == {"orchestration.schedule": "0 6 * * *"}
    assert resolver.extract(
        "this ordinary sentence has five words",
        [cron],
        allow_plain_fallback=False,
    ) == {}
    assert resolver.extract(
        "rocket",
        [identifier],
        allow_plain_fallback=False,
    ) == {}


def test_history_extracts_one_cron_fragment_from_a_larger_message():
    resolver = HeuristicResolver(specialized_resolvers=())
    requirement = Requirement(
        path="custom.schedule",
        question="schedule",
        value_schema={
            "type": "string",
            "pattern": r"^\S+(?:\s+\S+){4}$",
            "description": "Harmonogram w formacie Linux cron.",
        },
    )

    assert resolver.extract(
        "owner: team-a\nschedule: 0 6 * * *\nuri: gs://raw/orders.csv",
        [requirement],
        allow_plain_fallback=False,
    ) == {"custom.schedule": "0 6 * * *"}


def test_array_parser_ignores_incomplete_label_lines_in_a_mixed_message():
    resolver = HeuristicResolver(specialized_resolvers=())
    requirement = array_object_requirement()

    parsed = resolver.parse_structured(
        "source system: SAP\n"
        "pipeline: sap_orders\n"
        "owner: team-a@example.com\n"
        "order_id STRING\n"
        "amount NUMERIC",
        requirement,
    )

    assert parsed is not None
    assert parsed.complete
    assert parsed.value == [
        {"name": "order_id", "dataType": "STRING"},
        {"name": "amount", "dataType": "NUMERIC"},
    ]


def test_schema_driven_scalar_handlers_do_not_depend_on_paths():
    resolver = HeuristicResolver(specialized_resolvers=())
    requirements = [
        Requirement(
            path="custom.classification",
            question="classification",
            value_schema={"type": "string", "enum": ["PUBLIC", "INTERNAL"]},
        ),
        Requirement(
            path="custom.enabled",
            question="enabled",
            value_schema={"type": "boolean"},
        ),
        Requirement(
            path="custom.retries",
            question="retries",
            value_schema={"type": "integer", "minimum": 0, "maximum": 5},
        ),
    ]

    assert resolver.extract(
        "internal",
        requirements[:1],
        allow_plain_fallback=True,
    ) == {"custom.classification": "INTERNAL"}
    assert resolver.extract(
        "tak",
        requirements[1:2],
        allow_plain_fallback=True,
    ) == {"custom.enabled": True}
    assert resolver.extract(
        "3",
        requirements[2:],
        allow_plain_fallback=True,
    ) == {"custom.retries": 3}
    assert resolver.extract(
        "8",
        requirements[2:],
        allow_plain_fallback=True,
    ) == {}


def test_labeled_owner_correction_does_not_keep_the_correction_word():
    resolver = HeuristicResolver()
    requirement = Requirement(
        path="metadata.owner",
        question="owner",
        value_schema={"type": "string"},
    )

    assert resolver.extract(
        "owner jednak team_b",
        [requirement],
        allow_plain_fallback=False,
    ) == {"metadata.owner": "team_b"}
    assert resolver.extract(
        "gs://raw-zone/sap/owner.csv",
        [requirement],
        allow_plain_fallback=False,
    ) == {}
    assert resolver.extract(
        "stage07_owner_correction",
        [requirement],
        allow_plain_fallback=False,
    ) == {}


def test_exact_enum_wins_even_when_choices_are_too_similar_for_fuzzy_matching():
    resolver = HeuristicResolver(specialized_resolvers=())
    requirement = Requirement(
        path="metadata.deliveryMode",
        question="Tryb dostawy?",
        value_schema={
            "type": "string",
            "enum": ["DELIVERY_MODE_A", "DELIVERY_MODE_B"],
        },
    )

    assert resolver.extract(
        "delivery_mode_a",
        [requirement],
        allow_plain_fallback=True,
    ) == {"metadata.deliveryMode": "DELIVERY_MODE_A"}


def test_schema_format_extracts_uri_and_date_from_history():
    resolver = HeuristicResolver(specialized_resolvers=())
    uri = Requirement(
        path="custom.location",
        question="location",
        value_schema={
            "type": "string",
            "format": "uri",
            "pattern": r"^(gs|s3)://.+",
        },
    )
    start_date = Requirement(
        path="custom.start",
        question="start",
        value_schema={"type": "string", "format": "date"},
    )

    assert resolver.extract(
        "Plik jest w gs://raw-zone/data.csv, gotowy.",
        [uri],
        allow_plain_fallback=False,
    ) == {"custom.location": "gs://raw-zone/data.csv"}
    assert resolver.extract(
        "Start zaplanowano na 2026-08-21.",
        [start_date],
        allow_plain_fallback=False,
    ) == {"custom.start": "2026-08-21"}


def test_unsupported_schema_accepts_only_explicit_json_representation():
    resolver = HeuristicResolver(specialized_resolvers=())
    requirement = Requirement(
        path="custom.mode",
        question="mode",
        value_schema={},
        unsupported_schema_keywords=["anyOf"],
    )

    assert resolver.extract(
        "batch",
        [requirement],
        allow_plain_fallback=True,
    ) == {}
    assert resolver.extract(
        '"batch"',
        [requirement],
        allow_plain_fallback=True,
    ) == {"custom.mode": "batch"}
