"""Optional Pydantic AI implementation of SemanticInterpreterPort.

Importing this module requires the `ai` extra. The rest of ADCM does not.
"""
from __future__ import annotations

from adcm.domain.models import AgentContext, TurnInterpretation

try:
    from pydantic_ai import Agent
except ImportError as exc:  # pragma: no cover - depends on optional dependency
    Agent = None  # type: ignore[assignment]
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


SYSTEM_PROMPT = """
You are the semantic interpretation component of ADCM.
Return only the structured TurnInterpretation output.

Rules:
- Extract semantic concepts, not invented contract paths.
- Treat facts that may map later as schema-agnostic signals.
- Treat broad statements such as 'always UTF-8' or 'we do not use encryption' as preferences.
- If the user clearly replaces an earlier value, emit a correction.
- If replacement intent is uncertain, mark the correction uncertain rather than changing state.
- Detect likely typos and suggest a canonical candidate, but do not silently rewrite business values.
- Never invent required fields, workflow order, defaults, enrichments, or schema paths.
- Contract Forge is the schema authority; you are not.
""".strip()


class PydanticAIInterpreter:
    def __init__(self, model: str):
        if Agent is None:  # pragma: no cover
            raise RuntimeError("Install ADCM with the 'ai' extra") from _IMPORT_ERROR
        self.agent = Agent(model, output_type=TurnInterpretation, instructions=SYSTEM_PROMPT)

    async def interpret_turn(self, text: str, context: AgentContext) -> TurnInterpretation:
        prompt = (
            "Current ADCM context (authoritative application state projection):\n"
            f"{context.model_dump_json(indent=2)}\n\n"
            "New user message:\n"
            f"{text}"
        )
        result = await self.agent.run(prompt)
        return result.output
