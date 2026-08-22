#!/usr/bin/env python3
import asyncio
from fastapi import HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
from src.utils.assistant_singleton import get_assistant
from src.utils.message_queue import message_queue_manager
from src.utils.config import load_config
from src.utils.service_base import create_service_app, run_service

app, logger = create_service_app(
    "Bayesian-AGI-Core Memory Service",
    "Memory Service for Bayesian-AGI-Core",
    "memory",
)


class MemoryRequest(BaseModel):
    content: str
    metadata: Optional[Dict] = None


async def startup_event():
    config = load_config()
    await get_assistant().initialize(config)
    try:
        message_queue_manager.connect()
        message_queue_manager.subscribe("memory_queue", handle_memory_message)
        asyncio.create_task(asyncio.to_thread(message_queue_manager.start_consuming))
        logger.info("Message queue initialized")
    except Exception as e:
        logger.warning("Message queue init failed: %s", e)


def handle_memory_message(message):
    try:
        msg_type = message.get("type")
        if msg_type == "add_memory":
            asyncio.create_task(get_assistant().add_memory(
                message.get("content"), message.get("metadata")))
            logger.info("Add memory: %s", message.get("content"))
        elif msg_type == "retrieve_memories":
            asyncio.create_task(get_assistant().retrieve_memories(
                message.get("query"), message.get("top_k", 5)))
            logger.info("Retrieve memories: %s", message.get("query"))
        else:
            logger.warning("Unknown message type: %s", msg_type)
    except Exception as e:
        logger.error("Handle message failed: %s", e)


@app.on_event("startup")
async def _startup():
    await startup_event()


@app.post("/api/memory")
async def add_memory(req: MemoryRequest):
    try:
        memory_id = await get_assistant().add_memory(content=req.content, metadata=req.metadata)
        return {"id": memory_id, "message": "Memory added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add memory: {e}")


@app.get("/api/memory/search")
async def search_memory(query: str, top_k: int = 5):
    try:
        memories = await get_assistant().retrieve_memories(query, top_k)
        return {"memories": memories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search memory: {e}")


if __name__ == "__main__":
    run_service("src.memory_service", port=8002)
