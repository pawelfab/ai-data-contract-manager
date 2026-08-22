from fastapi import FastAPI
from adcm.bootstrap.container import build_container
from .routes import router

def create_app() -> FastAPI:
    app=FastAPI(title="AI Data Contract Manager",version="0.4.0")
    app.state.container=build_container()
    app.include_router(router)
    return app
