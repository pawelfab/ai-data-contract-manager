from adcm.cli import _uses_multiline_input
from adcm.models import Requirement


def test_multiline_input_is_selected_by_array_object_shape_not_path():
    requirement = Requirement(
        path="custom.dataset.fields",
        question="Podaj pola.",
        value_schema={
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name"],
                "properties": {"name": {"type": "string"}},
            },
        },
    )

    assert _uses_multiline_input(requirement) is True
    assert _uses_multiline_input(
        Requirement(
            path="source.columns",
            question="Nie jest tablicą.",
            value_schema={"type": "string"},
        )
    ) is False
