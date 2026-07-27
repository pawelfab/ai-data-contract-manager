from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from pydantic_ai import Agent
from starlette.applications import Starlette

from .dependencies import AppDeps


def create_web_app(
    agent: Agent[AppDeps, str],
    deps: AppDeps,
) -> Starlette:
    """Create the Pydantic AI UI and bind dependency lifecycle to ASGI."""

    app = agent.to_web(deps=deps)
    base_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(
        application: Starlette,
    ) -> AsyncIterator[dict | None]:
        async with base_lifespan(application) as state:
            await deps.contract_port.start()
            try:
                yield state
            finally:
                await deps.contract_port.close()

    app.router.lifespan_context = lifespan
    return app
