#!/usr/bin/env python3
from src.utils.assistant_singleton import get_assistant
from src.utils.service_base import create_service_app, run_service

app, logger = create_service_app(
    "Bayesian-AGI-Core LLM Service",
    "LLM Service for Bayesian-AGI-Core",
    "llm",
    with_assistant=True,
)


@app.get("/api/models")
async def get_models():
    models = get_assistant().get_models()
    logger.info("Models: %s", models)
    return {"models": models}


if __name__ == "__main__":
    run_service("src.llm_service", port=8001)
