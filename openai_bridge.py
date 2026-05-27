#!/usr/bin/env python3
"""
OpenAI-compatible API bridge for local Ollama

Translates OpenAI /v1/chat/completions requests to Ollama's API.
Falls back to 衡枢Agent if Ollama is unavailable.
Supports streaming (SSE) and multi-model.
"""
import asyncio
import json
import logging
import os
import time
from typing import Optional, List, AsyncGenerator

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("openai_bridge")

HENGSHU_URL = os.getenv("HENGSHU_URL", "http://hengshu-agent:8000")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://192.168.3.105:11434")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemma4:e4b")

app = FastAPI(title="OpenAI Bridge for Ollama + 衡枢Agent")
client = httpx.AsyncClient(timeout=300)


class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = DEFAULT_MODEL
    messages: List[ChatMessage]
    stream: Optional[bool] = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


async def _call_ollama(messages: list, model: str, stream: bool = False):
    payload = {"model": model, "messages": messages, "stream": stream}
    return await client.post(f"{OLLAMA_URL}/v1/chat/completions", json=payload)


async def _stream_ollama(messages: list, model: str):
    async with client.stream("POST", f"{OLLAMA_URL}/v1/chat/completions",
                             json={"model": model, "messages": messages, "stream": True}) as resp:
        async for line in resp.aiter_lines():
            if line.startswith("data: "):
                yield f"{line}\n\n"
                if line.strip() == "data: [DONE]":
                    break


async def _call_hengshu(text: str, model: str) -> str:
    try:
        resp = await client.post(
            f"{HENGSHU_URL}/api/chat/v3",
            json={"session_id": f"bridge-{time.time()}", "message": text, "model": model},
        )
        body = (await resp.aread()).decode()
        for line in body.split("\n"):
            line = line.strip()
            if line.startswith("data: "):
                try:
                    chunk = json.loads(line[6:])
                    c = chunk.get("data", {}).get("content", "")
                    if c:
                        return c
                except json.JSONDecodeError:
                    continue
        return body[:500]
    except Exception as e:
        return f"Error: {e}"


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest, raw: Request):
    if req.stream:
        return await _handle_stream(req)
    return await _handle_sync(req)


async def _handle_sync(req: ChatCompletionRequest):
    last = req.messages[-1] if req.messages else ChatMessage(role="user", content="")
    ollama_messages = [{"role": m.role, "content": m.content} for m in req.messages]

    try:
        resp = await _call_ollama(ollama_messages, req.model)
        data = resp.json()
        reply = data["choices"][0]["message"]["content"] if data.get("choices") else ""
    except Exception as e:
        logger.warning(f"Ollama failed ({e}), fallback to Hengshu...")
        reply = await _call_hengshu(last.content, req.model)

    return JSONResponse({
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": reply}, "finish_reason": "stop"}],
    })


async def _handle_stream(req: ChatCompletionRequest):
    ollama_messages = [{"role": m.role, "content": m.content} for m in req.messages]

    async def event_stream():
        try:
            async for chunk in _stream_ollama(ollama_messages, req.model):
                yield chunk
        except Exception as e:
            logger.warning(f"Ollama stream failed ({e}), fallback...")
            reply = await _call_hengshu(req.messages[-1].content if req.messages else "", req.model)
            yield f"data: {json.dumps({'choices':[{'delta':{'content':reply}}]})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/v1/models")
async def list_models():
    try:
        resp = await client.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            return {
                "object": "list",
                "data": [{"id": m["name"], "object": "model", "created": int(time.time())} for m in models]
            }
    except Exception:
        pass
    return {"object": "list", "data": [{"id": DEFAULT_MODEL, "object": "model"}]}


@app.get("/health")
async def health():
    ollama_ok = False
    try:
        r = await client.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        ollama_ok = r.status_code == 200
    except Exception:
        pass
    return {
        "status": "ok", "ollama": ollama_ok,
        "default_model": DEFAULT_MODEL,
        "ollama_url": OLLAMA_URL,
    }


@app.on_event("shutdown")
async def shutdown():
    await client.aclose()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8001"))
    logger.info(f"Starting bridge on port {port}, Ollama: {OLLAMA_URL}, fallback: {HENGSHU_URL}")
    uvicorn.run(app, host="0.0.0.0", port=port)
