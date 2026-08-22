#!/usr/bin/env python3
from fastapi import HTTPException
from src.utils.assistant_singleton import get_assistant
from src.utils.service_base import create_service_app, run_service

app, logger = create_service_app(
    "Bayesian-AGI-Core Cognition Service",
    "Cognition Service for Bayesian-AGI-Core",
    "cognition",
    with_assistant=True,
)


@app.post("/api/decision")
async def make_decision(possible_actions: list):
    try:
        decision = get_assistant().make_decision(possible_actions)
        return {"decision": decision}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to make decision: {e}")


if __name__ == "__main__":
    run_service("src.cognition_service", port=8003)
