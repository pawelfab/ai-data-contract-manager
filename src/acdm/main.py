from __future__ import annotations

import uvicorn

from .agent import create_agent
from .settings import AppSettings
from .web_app import create_web_app

settings = AppSettings.from_env()
agent, deps = create_agent(settings)
app = create_web_app(agent, deps)


def run() -> None:
    uvicorn.run(
        "acdm.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    run()
