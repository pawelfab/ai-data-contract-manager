"""Optional PydanticAI adapter. Install `requirements-ai.txt` and select it in wiring in a later iteration."""

from pydantic_ai import Agent, PromptedOutput

from adcm.domain.forge import ForgeDescription
from adcm.domain.turn import IntentResolution


class PydanticAIIntentResolver:
    def __init__(self, model: str) -> None:
        self.agent = Agent(
            model,
            ##output_type=IntentResolution, to nie działa z lokalny api bo uzywa tool output którego nie obsługuje lokalnie, musi byc jak nizej przez PromptedOutput
            output_type=PromptedOutput(IntentResolution),
            instructions=(
                "Convert the user message into generic contract mutation candidates. "
                "Never mutate state, never invent contract paths, and return confidence for each candidate."
            ),
        )

    async def resolve(self, message: str, *, document: dict, definition: ForgeDescription | None = None) -> IntentResolution:
        known_fields = [] if definition is None else [item.model_dump(mode="json") for item in definition.fields]
        prompt = f"Current document: {document}\nKnown contract fields: {known_fields}\nUser: {message}"
        result = await self.agent.run(prompt)
        return result.output
