#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ollama LLM 服务 - 基于 BaseLLM 实现，兼容 LLMRouter
"""

import httpx
import json
from typing import List, Dict, AsyncGenerator, Any, Optional
from datetime import datetime

from ..llm.base_llm import BaseLLM, LLMConfig, LLMResponse, Message


class OllamaLLM(BaseLLM):
    """Ollama LLM 服务"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.base_url or "http://localhost:11434"

    async def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        messages = [Message(role="user", content=prompt)]
        return await self.chat(messages, temperature=temperature, max_tokens=max_tokens, **kwargs)

    async def chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
        }
        if temperature is not None:
            payload["options"] = {"temperature": temperature}

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data.get("message", {}).get("content", "")

        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.provider,
            usage={"input_tokens": 0, "output_tokens": len(content)},
        )

    async def stream_chat(
        self, messages: List[Dict], tools: List[Dict] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        payload = {"model": self.model, "messages": messages, "stream": True}
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as resp:
                async for chunk in resp.aiter_lines():
                    if chunk.strip():
                        try:
                            data = json.loads(chunk)
                            if "message" in data:
                                yield {"content": data["message"].get("content", "")}
                        except json.JSONDecodeError:
                            continue

    async def get_available_models(self) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/api/tags", timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    return [
                        {"name": m["name"], "size": m.get("size", 0)}
                        for m in data.get("models", [])
                    ]
        except Exception:
            pass
        return []

    def get_available_models_sync(self) -> List[Dict[str, Any]]:
        try:
            with httpx.Client() as client:
                resp = client.get(f"{self.base_url}/api/tags", timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    return [
                        {"name": m["name"], "size": m.get("size", 0)}
                        for m in data.get("models", [])
                    ]
        except Exception:
            pass
        return []

    def get_model_info(self) -> Dict[str, Any]:
        return {"provider": self.provider, "model": self.model, "base_url": self.base_url}

    def is_available(self) -> bool:
        try:
            with httpx.Client() as client:
                resp = client.get(f"{self.base_url}/api/tags", timeout=5)
                return resp.status_code == 200
        except Exception:
            return False
