# Implementation roadmap

This reference package contains corrected domain/workflow contracts and tests. The production implementation should be split into stage specs generated from `PROMPT_STAGE_SPEC_GENERATOR.md`.

Recommended capability order:

1. repository/config ownership cleanup;
2. domain model + path/array/evidence invariants;
3. ADCM workflow and reprojection;
4. real stateless Contract Forge adapter/server contract;
5. Pydantic AI semantic interpreter;
6. durable persistence/audit;
7. API/chat endpoints;
8. Web UI draft/YAML read models;
9. end-to-end hardening and real contract integration tests.

The exact stage numbering should follow the current accepted `IMPLEMENTATION_PLAN.md` in the target repository. Do not use this roadmap as a substitute for stage specifications.

For every stage use `docs/STAGE_SPEC_TEMPLATE.md`. Keep architecture-heavy contracts in the spec and leave private implementation details to the coding model.
