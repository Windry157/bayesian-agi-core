#!/usr/bin/env python3
"""
OpenAI-compatible API bridge for 衡枢Agent

Translates OpenAI /v1/chat/completions requests to 衡枢Agent's API.
Run as a sidecar alongside hengshu-agent:
    python openai_bridge.py
"""
import asyncio
import json
import logging
import os
from typing import Optional, List

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("openai_bridge")

HENGSHU_URL = os.getenv("HENGSHU_URL", "http://hengshu-agent:8000")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://192.168.3.105:11434")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemma4:e4b")

app = FastAPI(title="OpenAI Bridge for 衡枢Agent")

client = httpx.AsyncClient(timeout=300)


# === OpenAI-compatible request/response models ===

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = DEFAULT_MODEL
    messages: List[ChatMessage]
    stream: Optional[bool] = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[dict]
    usage: dict = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


# === OpenAI-compatible endpoint ===

@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    last = req.messages[-1] if req.messages else ChatMessage(role="user", content="")
    message_text = last.content

    try:
        ollama_messages = [{"role": m.role, "content": m.content} for m in req.messages]
        resp = await client.post(
            f"{OLLAMA_URL}/v1/chat/completions",
            json={
                "model": req.model,
                "messages": ollama_messages,
                "stream": False,
            },
        )
        data = resp.json()
        reply = data["choices"][0]["message"]["content"] if data.get("choices") else ""
    except Exception as e:
        logger.warning(f"Ollama direct call failed ({e}), falling back to Hengshu...")
        try:
            resp = await client.post(
                f"{HENGSHU_URL}/api/chat/v3",
                json={"session_id": f"bridge-{id(req)}", "message": message_text, "model": req.model},
            )
            body = (await resp.aread()).decode()
            reply = body
            for line in body.split("\n"):
                line = line.strip()
                if line.startswith("data: "):
                    try:
                        chunk = json.loads(line[6:])
                        c = chunk.get("data", {}).get("content", "")
                        if c:
                            reply = c
                    except json.JSONDecodeError:
                        continue
        except Exception as e2:
            logger.error(f"Hengshu fallback also failed: {e2}")
            reply = f"Error: {e2}"

    import time
    return ChatCompletionResponse(
        id=f"chatcmpl-{int(time.time())}",
        created=int(time.time()),
        model=req.model,
        choices=[{
            "index": 0,
            "message": {"role": "assistant", "content": reply},
            "finish_reason": "stop",
        }],
    )


@app.get("/health")
async def health():
    return {"status": "ok", "hengshu_url": HENGSHU_URL, "default_model": DEFAULT_MODEL}


@app.on_event("shutdown")
async def shutdown():
    await client.aclose()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8001"))
    logger.info(f"Starting OpenAI bridge on port {port}, proxying to {HENGSHU_URL}")
    uvicorn.run(app, host="0.0.0.0", port=port)
