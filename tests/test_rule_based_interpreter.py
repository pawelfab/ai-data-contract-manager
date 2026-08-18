import pytest

from adcm.adapters.llm.rule_based_interpreter import RuleBasedInterpreter
from adcm.domain.models import AgentContext


EMPTY_CONTEXT = AgentContext(
    current_stage=None,
    active_signals=[],
    active_preferences=[],
    known_values={},
    allowed_paths=[],
    pending_requirements=[],
    recent_messages=[],
)


@pytest.mark.asyncio
@pytest.mark.parametrize("phrase", ["CSV ze średnikiem", "CSV ze srednikiem", "CSV ;"])
async def test_demo_interpreter_recognizes_delimiter_variants(phrase):
    result = await RuleBasedInterpreter().interpret_turn(phrase, EMPTY_CONTEXT)
    assert any(s.concept == "field_delimiter" and s.value == ";" for s in result.extracted_signals)
