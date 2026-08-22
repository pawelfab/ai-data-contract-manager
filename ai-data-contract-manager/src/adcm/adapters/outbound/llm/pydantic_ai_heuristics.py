import json
from typing import Any

from pydantic_ai import Agent, PromptedOutput

from adcm.application.ports.llm import (
    HeuristicsPort,
    QuestionRequest,
    QuestionResult,
    ResolveRequest,
    ResolveResult,
)
from adcm.domain.evidence.models import EvidenceItem
from adcm.domain.issues.models import AdvisoryIssue


_MISSING_FIELDS_RULE = """
Missing required fields are owned by Contract Forge.
Do not report a missing required field as a heuristic inconsistency.
Do not report an inconsistency solely because one field of an object is present while another
required sibling field is missing. A missing field alone is never a heuristic warning and never
requires_user_decision.
""".strip()

_RESOLVER_INSTRUCTIONS = f"""
You are the heuristic interpretation layer of AI Data Contract Manager.
You do not control workflow and you never mutate the contract yourself.
Match only values supported by supplied evidence to the exact requirements supplied by ADCM.
Also recognize an explicit user edit of a path/value that already exists in current_document,
even when there are no unresolved requirements. Do not invent new contract paths.
For an existing array, an explicit request to add/change an element may return the whole updated
array value at the existing array path when no more specific requirement is available.
The same evidence may contain values for requirements discovered later, so inspect all supplied
evidence and chat history. Prefer the latest explicit correction by the user.
Never invent a value and never silently correct a suspected typo.
Every candidate MUST reference the evidence_id that supports it.
If sources disagree, report a warning rather than deciding secretly.

You may normalize an unambiguous natural-language value into the standard machine-readable format
explicitly required by the requirement description. Example: if a field explicitly expects a cron
expression, "every day at 7am" may become "0 7 * * *". Do not normalize when meaning is ambiguous.

{_MISSING_FIELDS_RULE}
""".strip()

_CONSISTENCY_INSTRUCTIONS = f"""
Act only as a semantic inconsistency detector. Report contradictory evidence, suspicious semantic
inconsistencies, mutually conflicting candidate meanings, or likely typos. Do not rewrite values.
Set requires_user_decision=true only when a material human choice is needed.
{_MISSING_FIELDS_RULE}
""".strip()

_QUESTION_INSTRUCTIONS = """
Compose one concise response in the language used by the user.
Do not ask again for facts already visible in history or current_document.
For unresolved fields, use ONLY naming/meaning supplied by Contract Forge:
- prefer display_name, otherwise title;
- use help_text/description when useful;
- always include the canonical JSON path in parentheses for identifiers or whenever meaning could
  be ambiguous;
- never invent business-friendly meanings such as "configuration ID" unless Forge supplied that
  meaning explicitly.
Example preferred form: `Data File ID (/metadata/dataFileId) — <Forge description>`.
Separately surface only warnings that are genuinely useful to the user. Do not turn ordinary
missing fields into warnings and do not choose a value on the user's behalf.
""".strip()


class PydanticAiHeuristicsAdapter(HeuristicsPort):
    def __init__(
        self,
        model: str,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        model_spec: Any = _model_spec(model, base_url=base_url, api_key=api_key)
        self.resolve_agent = Agent(
            model_spec,
            output_type=PromptedOutput(ResolveResult),
            instructions=_RESOLVER_INSTRUCTIONS,
            retries={"output": 2},
        )
        self.consistency_agent = Agent(
            model_spec,
            output_type=PromptedOutput(list[AdvisoryIssue]),
            instructions=_CONSISTENCY_INSTRUCTIONS,
            retries={"output": 2},
        )
        self.question_agent = Agent(
            model_spec,
            output_type=PromptedOutput(QuestionResult),
            instructions=_QUESTION_INSTRUCTIONS,
            retries={"output": 2},
        )

    async def resolve(self, request: ResolveRequest) -> ResolveResult:
        result = await self.resolve_agent.run(request.model_dump_json(indent=2))
        return result.output

    async def inspect_consistency(
        self, evidence: list[EvidenceItem], current_document: dict
    ) -> list[AdvisoryIssue]:
        payload = {
            "evidence": [item.model_dump(mode="json") for item in evidence],
            "current_document": current_document,
        }
        result = await self.consistency_agent.run(json.dumps(payload, ensure_ascii=False, default=str))
        return result.output

    async def compose_question(self, request: QuestionRequest) -> str:
        result = await self.question_agent.run(request.model_dump_json(indent=2))
        return result.output.message


def _model_spec(model: str, *, base_url: str | None, api_key: str | None):
    if not base_url:
        return model
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    provider = OpenAIProvider(base_url=base_url, api_key=api_key or "local")
    return OpenAIChatModel(model, provider=provider)
