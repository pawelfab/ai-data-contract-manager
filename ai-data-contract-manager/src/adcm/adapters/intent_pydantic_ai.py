"""Optional PydanticAI adapter. Install `requirements-ai.txt` and select it in wiring in a later iteration."""

from pydantic_ai import Agent, PromptedOutput

from adcm.domain.forge import ForgeDescription
from adcm.domain.turn import IntentResolution


class PydanticAIIntentResolver:
    def __init__(self, model: str) -> None:
        self.agent = Agent(
            model,
            name="adcm_intent_resolver",
            # PromptedOutput is required by the configured local API, which does
            # not support the tool-output mode used by a bare output_type model.
            output_type=PromptedOutput(IntentResolution),
            instructions=(
                "Resolve the user message into IntentResolution. "
                "Use mutation only for an explicit request to change the contract, "
                "knowledge only for a request for information, mixed only when both "
                "are explicit, and unresolved when the message cannot be classified. "
                "A knowledge or unresolved result must have no mutation candidates. "
                "Do not infer a mutation candidate from a question or from the current "
                "document value. Never mutate state or invent contract paths, and "
                "return confidence for each candidate."
            ),
        )

    async def resolve(self, message: str, *, document: dict, definition: ForgeDescription | None = None) -> IntentResolution:
        known_fields = [] if definition is None else [item.model_dump(mode="json") for item in definition.fields]
        prompt = f"Current document: {document}\nKnown contract fields: {known_fields}\nUser: {message}"
        result = await self.agent.run(prompt)
        return result.output
