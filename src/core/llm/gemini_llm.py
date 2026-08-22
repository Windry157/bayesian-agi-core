#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Gemini LLM集成
使用Google AI API调用Gemini模型

模型支持：
- Gemini 2.0 Flash (gemini-2.0-flash)
- Gemini 1.5 Flash (gemini-1.5-flash)
- Gemini 1.5 Pro (gemini-1.5-pro)
- Gemini 1.0 Pro (gemini-1.0-pro)
"""

import logging
from typing import Dict, List, Optional, Any
import os

from .base_llm import BaseLLM, LLMConfig, LLMResponse, Message, LLMFactory

logger = logging.getLogger(__name__)

# 注册到工厂
LLMFactory.register_provider("gemini", None)  # 延迟导入


class GeminiLLM(BaseLLM):
    """Google Gemini LLM实现

    使用Google AI API进行通信。
    """

    DEFAULT_MODEL = "gemini-1.5-flash"
    SUPPORTED_MODELS = [
        "gemini-2.0-flash",
        "gemini-2.0-flash-exp",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-1.0-pro",
        "gemini-1.0-pro-vision",
    ]

    def __init__(self, config: LLMConfig):
        """初始化Gemini LLM

        Args:
            config: LLM配置
        """
        super().__init__(config)

        self.api_key = config.api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            logger.warning("GOOGLE_API_KEY not set")

        self.model = config.model or self.DEFAULT_MODEL
        self.base_url = "https://generativelanguage.googleapis.com"
        self.client = None

        logger.info(f"GeminiLLM initialized with model: {self.model}")

    def _get_client(self):
        """获取HTTP客户端"""
        if self.client is None:
            try:
                import httpx
                self.client = httpx.Client(
                    timeout=self.config.timeout
                )
            except ImportError:
                raise ImportError("httpx required for Gemini. Run: pip install httpx")

        return self.client

    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """生成文本

        Args:
            prompt: 提示词
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数

        Returns:
            LLMResponse
        """
        messages = [Message(role="user", content=prompt)]
        return self.chat(messages, temperature, max_tokens, **kwargs)

    def chat(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """对话

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数

        Returns:
            LLMResponse
        """
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not set")

        # 转换消息格式
        contents = []
        for msg in messages:
            contents.append({
                "role": "user" if msg.role == "user" else "model",
                "parts": [{"text": msg.content}]
            })

        # 构建请求
        request_data = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature or self.config.temperature,
                "maxOutputTokens": max_tokens or self.config.max_tokens
            }
        }

        # 添加可选参数
        if "system_instruction" in kwargs:
            request_data["systemInstruction"] = {
                "parts": [{"text": kwargs["system_instruction"]}]
            }

        if "top_p" in kwargs:
            request_data["generationConfig"]["topP"] = kwargs["top_p"]

        if "top_k" in kwargs:
            request_data["generationConfig"]["topK"] = kwargs["top_k"]

        try:
            client = self._get_client()
            url = f"{self.base_url}/v1beta/models/{self.model}:generateContent?key={self.api_key}"

            response = client.post(url, json=request_data)

            if response.status_code != 200:
                error_msg = f"API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)

            result = response.json()

            # 提取响应内容
            text = ""
            if "candidates" in result and len(result["candidates"]) > 0:
                candidate = result["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    for part in candidate["content"]["parts"]:
                        if "text" in part:
                            text += part["text"]

            # 提取使用信息
            usage = {}
            if "usageMetadata" in result:
                usage = {
                    "prompt_tokens": result["usageMetadata"].get("promptTokenCount", 0),
                    "completion_tokens": result["usageMetadata"].get("candidatesTokenCount", 0),
                    "total_tokens": result["usageMetadata"].get("totalTokenCount", 0)
                }

            return LLMResponse(
                content=text,
                model=self.model,
                provider="gemini",
                usage=usage,
                finish_reason=result.get("candidates", [{}])[0].get("finishReason") if result.get("candidates") else None,
                metadata=result
            )

        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            raise

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息

        Returns:
            模型信息字典
        """
        return {
            "provider": "gemini",
            "model": self.model,
            "supported_models": self.SUPPORTED_MODELS,
            "api_endpoint": self.base_url,
            "capabilities": [
                "chat",
                "vision",
                "function_calling"
            ]
        }

    def is_available(self) -> bool:
        """检查模型是否可用

        Returns:
            是否可用
        """
        if not self.api_key:
            return False

        try:
            # 尝试简单的API调用测试
            client = self._get_client()
            url = f"{self.base_url}/v1beta/models/{self.model}?key={self.api_key}"
            response = client.get(url)
            return response.status_code == 200
        except Exception:
            return False

    def __del__(self):
        """清理资源"""
        if self.client:
            self.client.close()


# 注册到工厂
LLMFactory.register_provider("gemini", GeminiLLM)
