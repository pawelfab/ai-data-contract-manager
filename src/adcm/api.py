from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from .orchestrator import ADCMOrchestrator
from .runtime import build_orchestrator
from .settings import load_settings


class MessageRequest(BaseModel):
    message: str


def create_app(orchestrator: ADCMOrchestrator | None = None) -> FastAPI:
    holder: dict[str, ADCMOrchestrator] = {}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        service = orchestrator or build_orchestrator(local_forge=False)
        holder["service"] = service
        app.state.orchestrator = service
        async with service.gateway:
            try:
                yield
            finally:
                await service.semantic.close()
        holder.clear()

    app = FastAPI(title="ADCM Minimal API", version="0.1.0", lifespan=lifespan)

    def service() -> ADCMOrchestrator:
        if "service" not in holder:
            raise RuntimeError("Application lifespan is not running")
        return holder["service"]

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/sessions")
    async def start_session() -> dict[str, Any]:
        return (await service().start()).model_dump(mode="json")

    @app.post("/sessions/{session_id}/messages")
    async def send_message(session_id: str, body: MessageRequest) -> dict[str, Any]:
        try:
            return (await service().message(session_id, body.message)).model_dump(mode="json")
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Unknown ADCM session") from exc

    @app.get("/sessions/{session_id}")
    async def get_session(session_id: str) -> dict[str, Any]:
        try:
            state = await service().state(session_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Unknown ADCM session") from exc
        return state.model_dump(mode="json")

    return app


app = create_app()


def main() -> None:
    import uvicorn

    settings = load_settings()
    uvicorn.run(
        "adcm.api:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
