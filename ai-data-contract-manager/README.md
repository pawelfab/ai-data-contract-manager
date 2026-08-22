# AI Data Contract Manager

ADCM is the conversational service. It owns sessions, evidence/provenance, PydanticAI semantic reasoning, optional context MCP tools and the deterministic Contract Forge stabilization loop.

Forge is configured by `ADCM_FORGE_MCP_URL` and is not part of the PydanticAI agent toolset. Optional context servers are configured through `ADCM_CONTEXT_MCP_URLS`.

ADCM keeps the LLM behind `HeuristicsPort`. The current local compatibility path supports OpenAI-compatible `/v1/chat/completions` endpoints that do not implement tool calling by using PydanticAI `PromptedOutput`.

## Local startup

From `ai-data-contract-manager/` after installing the service into its own virtual environment:

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env  # Windows: copy .env.example .env
python -m adcm.main
```

Alternatively run the ASGI application directly:

```bash
uvicorn adcm.main:app --reload --host 127.0.0.1 --port 8000
```

`python -m adcm.main` is supported by the service entrypoint and starts Uvicorn. Merely importing `adcm.main:app` never starts a server, which remains correct for Cloud Run/ASGI deployment.

## OpenAI through PydanticAI

Install dependencies from this service's `pyproject.toml` (the OpenAI optional group is included), then configure `.env`:

```env
ADCM_LLM_MODE=pydantic-ai
ADCM_LLM_MODEL=gpt-4o
# Optional for a local OpenAI-compatible endpoint:
ADCM_LLM_BASE_URL=http://127.0.0.1:1234/v1
OPENAI_API_KEY=local-or-real-key
```

The adapter constructs `OpenAIChatModel` with `OpenAIProvider`. Leave `ADCM_LLM_BASE_URL` empty for the official provider or set it for a compatible local endpoint. Keep API keys outside source control.
