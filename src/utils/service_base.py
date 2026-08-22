#!/usr/bin/env python3
import os
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from src.utils.config import load_config
from src.utils.assistant_singleton import get_assistant
from src.utils.prometheus_metrics import get_metrics_registry
from src.utils.structured_logging import get_logger
from src.core.monitoring import monitoring


def create_service_app(
    title: str,
    description: str,
    service_name: str,
    version: str = "1.0.0",
    cors_origins: list[str] | None = None,
    with_assistant: bool = False,
    with_metrics: bool = True,
) -> tuple[FastAPI, "logging.Logger"]:
    logger = get_logger(service_name)
    app = FastAPI(title=title, description=description, version=version)

    origins = cors_origins or ["http://localhost:8000", "http://127.0.0.1:8000"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    @app.get("/health")
    async def health_check():
        monitoring.record_request("GET", "/health", 200, 0)
        return {"status": "ok", "message": f"{title} is running"}

    @app.get("/")
    async def root():
        return {"message": f"Welcome to {title}", "version": version, "docs": "/docs"}

    if with_metrics:
        registry = get_metrics_registry()
        @app.get("/health/metrics")
        def metrics():
            try:
                return Response(content=registry.export(), media_type="text/plain")
            except Exception as e:
                logger.error("Metrics export failed: %s", e)
                return Response(content=f"Error: {e}", status_code=500)

    if with_assistant:
        assistant = get_assistant()
        @app.on_event("startup")
        async def startup():
            logger.info("Starting %s...", service_name)
            await assistant.initialize(load_config())
            logger.info("%s started successfully", service_name)

    return app, logger


def run_service(app_path: str, host: str = "0.0.0.0", port: int = 8000, workers: int = 1):
    import uvicorn
    reload_enabled = os.getenv("APP_ENV", "development") != "production"
    uvicorn.run(app_path, host=host, port=port, workers=workers, reload=reload_enabled)
