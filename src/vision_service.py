#!/usr/bin/env python3
import os, io, base64
from fastapi import HTTPException, UploadFile, File
from PIL import Image
import httpx
from src.utils.service_base import create_service_app, run_service

app, logger = create_service_app(
    "Bayesian-AGI-Core Vision Service",
    "Vision Service for Bayesian-AGI-Core",
    "vision",
)

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
VISION_MODEL = os.environ.get("VISION_MODEL", "gemma3:1b")

async def _call_ollama_vision(prompt: str, image_bytes: bytes) -> str:
    b64 = base64.b64encode(image_bytes).decode()
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{OLLAMA_URL}/api/chat", json={
            "model": VISION_MODEL,
            "messages": [{"role": "user", "content": prompt, "images": [b64]}],
            "stream": False, "options": {"temperature": 0.1}
        })
        r.raise_for_status()
        return r.json()["message"]["content"].strip()


@app.post("/api/vision/classify")
async def classify_image(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        Image.open(io.BytesIO(image_bytes)).verify()
        description = await _call_ollama_vision(
            "Classify this image in a single word (e.g. cat, dog, car, building, person, food, landscape). Return only the word.",
            image_bytes)
        classification = description.split()[0].strip().lower().rstrip(".,!?")
        logger.info("Classify: %s", classification)
        return {"classification": classification, "confidence": 0.0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classify failed: {e}")


@app.post("/api/vision/detect")
async def detect_objects(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        Image.open(io.BytesIO(image_bytes)).verify()
        result = await _call_ollama_vision(
            "List all objects you can see in this image. For each object, provide its name and approximate location "
            "(e.g. 'person at center-left, car at bottom-right'). Return as a bullet list.", image_bytes)
        logger.info("Detect: %s...", result[:200])
        return {"objects": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection failed: {e}")


@app.post("/api/vision/describe")
async def describe_image(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        Image.open(io.BytesIO(image_bytes)).verify()
        description = await _call_ollama_vision(
            "Describe this image in detail. Include objects, colors, composition, and any text you can see.",
            image_bytes)
        logger.info("Describe: %s...", description[:100])
        return {"description": description}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Describe failed: {e}")


if __name__ == "__main__":
    run_service("src.vision_service", port=8004)
