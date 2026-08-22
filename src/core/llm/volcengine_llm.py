#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火山引擎方舟大模型服务 - 基于 BaseLLM 实现，兼容 LLMRouter
支持 OpenAI 兼容接口，模型: doubao-code, doubao-seed-code
"""

import httpx
import json
from typing import List, Dict, Any, Optional
import logging

from ..llm.base_llm import BaseLLM, LLMConfig, LLMResponse, Message

logger = logging.getLogger(__name__)


class VolcEngineLLM(BaseLLM):
    """火山引擎方舟大模型服务"""

    DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.base_url or self.DEFAULT_BASE_URL
        self.api_key = config.api_key
        self._client = None

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.config.timeout or 60,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        messages = [Message(role="user", content=prompt)]
        return self.chat(messages, temperature=temperature, max_tokens=max_tokens, **kwargs)

    def chat(
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
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        client = self._get_client()
        try:
            resp = client.post(f"{self.base_url}/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()

            content = ""
            usage = None
            finish_reason = None

            if data.get("choices"):
                choice = data["choices"][0]
                if choice.get("message"):
                    content = choice["message"].get("content", "")
                finish_reason = choice.get("finish_reason")

            if data.get("usage"):
                usage = {
                    "input_tokens": data["usage"].get("prompt_tokens", 0),
                    "output_tokens": data["usage"].get("completion_tokens", 0),
                    "total_tokens": data["usage"].get("total_tokens", 0),
                }

            return LLMResponse(
                content=content,
                model=self.model,
                provider=self.provider,
                usage=usage,
                finish_reason=finish_reason,
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"VolcEngine API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"VolcEngine request failed: {e}")
            raise

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "api_key": "***" if self.api_key else None,
        }

    def is_available(self) -> bool:
        if not self.api_key:
            return False

        client = self._get_client()
        try:
            resp = client.get(f"{self.base_url}/models", timeout=10)
            if resp.status_code == 200:
                models = resp.json().get("data", [])
                model_names = [m.get("id") for m in models]
                return self.model in model_names
            return False
        except Exception as e:
            logger.debug(f"VolcEngine availability check failed: {e}")
            return False


from ..llm.base_llm import LLMFactory

LLMFactory.register_provider("volcengine", VolcEngineLLM)
LLMFactory.register_provider("volc", VolcEngineLLM)