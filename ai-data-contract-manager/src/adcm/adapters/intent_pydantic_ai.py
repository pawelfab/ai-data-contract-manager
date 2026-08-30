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
                "The intent_kind contract has exactly four rows: MUTATION means an "
                "explicit contract change (candidates allowed, knowledge_query null); "
                "KNOWLEDGE means an information request (candidates ignored and a "
                "non-blank knowledge_query required); MIXED means both explicit "
                "change and information request (candidates allowed and a non-blank "
                "query required); UNRESOLVED means the message cannot be classified "
                "(no candidates, no knowledge_query, and unresolved must contain a "
                "non-blank reason). "
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
