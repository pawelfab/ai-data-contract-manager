# ADCM reference architecture — corrected edition

This package consolidates the architecture decisions and fixes discovered during contract analysis and Stage 2 implementation.

Key properties:
- ADCM is stateful; Contract Forge is stateless.
- Forge receives the current nested draft snapshot on every evaluation.
- CurrentSchemaView replaces prior allowed paths; draft is reprojected after branch changes.
- Signals and user candidates require Evidence.
- Candidate provenance stays on ValueCandidate; ResolvedValue points to the winner.
- ContractDraft supports nested objects/arrays through ContractPath.
- `evaluate_draft`, `validate_final`, and `render_yaml` have separate semantics.
- YAML render happens once after turn stabilization and is cached by draft hash + schema revision + render mode.
- runtime template DSL is preserved for the Airflow DAG Generator.

Read in this order:
1. `docs/ISSUES_AND_RESOLUTIONS.md`
2. `docs/ARCHITECTURE.md`
3. `docs/DOMAIN_MODEL.md`
4. `docs/MCP_CONTRACT.md`
5. `docs/TURN_LIFECYCLE.md`
6. `docs/DESIGN_DECISIONS.md`
7. `LLM_REPO_GUIDE.md`
8. `PROMPT_STAGE_SPEC_GENERATOR.md`

Run:

```bash
python -m venv .venv
pip install -e '.[dev]'
pytest
```

Optional Pydantic AI adapter dependencies use the slim package via the `ai` extra.
