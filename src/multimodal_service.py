#!/usr/bin/env python3
from fastapi import HTTPException, UploadFile, File, Form
from PIL import Image
from src.core.multimodal.multimodal_processor import BasicMultimodalProcessor
from src.utils.service_base import create_service_app, run_service

app, logger = create_service_app(
    "Bayesian-AGI-Core Multimodal Service",
    "Multimodal Service for Bayesian-AGI-Core",
    "multimodal",
)

multimodal_processor = BasicMultimodalProcessor()


@app.post("/api/multimodal/text")
async def process_text(text: str = Form(...), task: str = Form(...)):
    try:
        return multimodal_processor.process(text, "text", task)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process text: {e}")


@app.post("/api/multimodal/image")
async def process_image(file: UploadFile = File(...), task: str = Form(...)):
    try:
        result = multimodal_processor.process(Image.open(file.file), "image", task)
        logger.info("Image processed: %s", result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process image: {e}")


@app.post("/api/multimodal/audio")
async def process_audio(file: UploadFile = File(...), task: str = Form(...)):
    try:
        audio = await file.read()
        result = multimodal_processor.process(audio, "audio", task)
        logger.info("Audio processed: %s", result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process audio: {e}")


@app.get("/api/multimodal/supported-input-types")
async def get_supported_input_types():
    return {"input_types": multimodal_processor.get_supported_input_types()}


@app.get("/api/multimodal/supported-tasks")
async def get_supported_tasks():
    return {"tasks": multimodal_processor.get_supported_tasks()}


if __name__ == "__main__":
    run_service("src.multimodal_service", port=8005)
