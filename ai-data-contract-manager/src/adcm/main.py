import os

from adcm.adapters.inbound.fastapi.app import create_app

app = create_app()


def main() -> None:
    """Local/process entrypoint.

    Importing ``adcm.main:app`` remains the preferred ASGI/deployment path.
    Running ``python -m adcm.main`` starts Uvicorn for local development.
    """
    import uvicorn

    host = os.getenv("ADCM_HOST", "127.0.0.1")
    port = int(os.getenv("ADCM_PORT", "8000"))
    reload_enabled = os.getenv("ADCM_RELOAD", "false").lower() in {"1", "true", "yes"}
    uvicorn.run("adcm.main:app", host=host, port=port, reload=reload_enabled)


if __name__ == "__main__":
    main()
