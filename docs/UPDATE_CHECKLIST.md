# ADCM — implementation completion checklist

Use this before finishing a code-change task.

## Scope and ownership

- [ ] I inspected the current implementation before editing.
- [ ] The change is implemented in the correct owner (ADCM vs Contract Forge vs Schema Explorer).
- [ ] I did not duplicate contract/schema logic in ADCM or UI.
- [ ] I did not give the LLM permission to mutate arbitrary contract paths.

## Behavior

- [ ] Source-system-first flow still works.
- [ ] Existing user facts are reused when later stair-step requirements appear.
- [ ] Invalid/partial user input produces a useful clarification instead of an unexplained repeated question.
- [ ] Forge still validates every canonical candidate.
- [ ] Value precedence/enrichment ordering is preserved unless intentionally changed.

## Dynamic schema/rules

- [ ] I did not hardcode a field that can be discovered through schema/Forge.
- [ ] Any new rule action/kind has an explicit deterministic handler and test.
- [ ] Unknown/incompatible rules fail or report diagnostics rather than being guessed from prose.

## Tests

- [ ] Added/updated focused unit tests.
- [ ] Added a regression test for the reported bug.
- [ ] Ran the relevant test subset.
- [ ] Ran the full suite if feasible.
- [ ] For transport/config changes, ran an end-to-end smoke test in the actual runtime environment.

## Documentation

- [ ] Updated `docs/CURRENT_STATE.md`.
- [ ] Updated `docs/DECISIONS.md` if a durable decision changed.
- [ ] Documented any code/docs inconsistency I found.
