# Changelog

## 0.4.0

- Added deterministic candidate decisions before any LLM-derived value reaches `ContractState`.
- Added evidence, confidence, path, type, authority and structural-conflict checks.
- Prevented scalar candidates from silently replacing existing object/list containers.
- Hardened JSON Pointer writes with `JsonPointerError` instead of raw `TypeError` on invalid intermediate structure.
- Added `CandidateOutcome.changed`; accepted-but-identical candidates no longer keep stabilization alive.
- Derived values are recomputed from the current Forge suggestions each round, preventing stale system enrichments after edits.
- Valid/complete contracts remain editable through chat; the first stabilization round still interprets the latest user evidence.
- User-facing warnings are a current fixed-point snapshot, not an accumulation of obsolete intermediate warnings.
- Missing requirements are no longer heuristic consistency warnings.
- Question generation uses Forge/schema titles, descriptions and canonical paths instead of inventing business meanings.
- Added unambiguous natural-language normalization guidance (including cron) while retaining deterministic validation.
- Added OpenAI-compatible local endpoint support with `OpenAIChatModel`, `OpenAIProvider` and `PromptedOutput` for endpoints without tool support.
- `.env` and service resources resolve relative to the service root.
- Inline `attachments: list[str]` are explicitly stored as `attachment_text` evidence; future file uploads remain an inbound-adapter concern.
- ADCM version updated to 0.4.0.
