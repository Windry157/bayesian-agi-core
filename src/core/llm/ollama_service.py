#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ollama LLM服务
"""

import httpx
from typing import List, Dict, AsyncGenerator, Any
from ..interfaces import ILLMService


class OllamaLLM(ILLMService):
    """Ollama LLM服务"""

    def __init__(self, config: Dict[str, Any]):
        """初始化Ollama LLM服务

        Args:
            config: 配置
        """
        self.ollama_url = config.get("ollama_url", "http://localhost:11434")
        self.default_model = config.get("default", "deepseek-r1:7b")

    async def stream_chat(
        self, messages: List[Dict], tools: List[Dict] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式聊天

        Args:
            messages: 消息列表
            tools: 工具列表

        Returns:
            流式生成的响应
        """
        url = f"{self.ollama_url}/api/chat"
        payload = {"model": self.default_model, "messages": messages, "stream": True}

        async with httpx.AsyncClient() as client:
            async with client.stream("POST", url, json=payload) as response:
                async for chunk in response.aiter_text():
                    if chunk:
                        yield {"content": chunk}

    async def get_available_models(self) -> List[Dict[str, Any]]:
        """获取可用模型

        Returns:
            模型列表
        """
        url = f"{self.ollama_url}/api/tags"

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                return [
                    {
                        "name": model["name"],
                        "size": model.get("size", 0),
                        "modified_at": model.get("modified_at", ""),
                    }
                    for model in data.get("models", [])
                ]
            return []

    def get_available_models_sync(self) -> List[Dict[str, Any]]:
        """同步获取可用模型

        Returns:
            模型列表
        """
        url = f"{self.ollama_url}/api/tags"

        with httpx.Client() as client:
            response = client.get(url)
            if response.status_code == 200:
                data = response.json()
                return [
                    {
                        "name": model["name"],
                        "size": model.get("size", 0),
                        "modified_at": model.get("modified_at", ""),
                    }
                    for model in data.get("models", [])
                ]
            return []
