#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Anthropic Claude LLM集成
使用Anthropic API调用Claude模型

模型支持：
- Claude 3.5 Sonnet (claude-3-5-sonnet-20241022)
- Claude 3 Opus (claude-3-opus-20240229)
- Claude 3 Sonnet (claude-3-sonnet-20240229)
- Claude 3 Haiku (claude-3-haiku-20240307)
"""

import logging
from typing import Dict, List, Optional, Any
import os

from .base_llm import BaseLLM, LLMConfig, LLMResponse, Message, LLMFactory

logger = logging.getLogger(__name__)

# 注册到工厂
LLMFactory.register_provider("anthropic", None)  # 延迟导入


class AnthropicLLM(BaseLLM):
    """Anthropic Claude LLM实现

    使用Anthropic API进行通信。
    """

    DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
    SUPPORTED_MODELS = [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet-20240620",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ]

    def __init__(self, config: LLMConfig):
        """初始化Anthropic LLM

        Args:
            config: LLM配置
        """
        super().__init__(config)

        self.api_key = config.api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY not set")

        self.model = config.model or self.DEFAULT_MODEL
        self.base_url = "https://api.anthropic.com"
        self.client = None

        logger.info(f"AnthropicLLM initialized with model: {self.model}")

    def _get_client(self):
        """获取HTTP客户端"""
        if self.client is None:
            try:
                import httpx
                self.client = httpx.Client(
                    base_url=self.base_url,
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json"
                    },
                    timeout=self.config.timeout
                )
            except ImportError:
                raise ImportError("httpx required for Anthropic. Run: pip install httpx")

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
        import json

        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        # 转换消息格式
        anthropic_messages = []
        for msg in messages:
            role = msg.role
            if role == "system":
                # Anthropic不支持system消息，需要特殊处理
                continue
            anthropic_messages.append({
                "role": role,
                "content": msg.content
            })

        # 构建请求
        request_data = {
            "model": self.model,
            "messages": anthropic_messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens
        }

        # 添加可选参数
        if "system" in kwargs:
            request_data["system"] = kwargs["system"]

        if "top_p" in kwargs:
            request_data["top_p"] = kwargs["top_p"]

        if "top_k" in kwargs:
            request_data["top_k"] = kwargs["top_k"]

        try:
            client = self._get_client()
            response = client.post("/v1/messages", json=request_data)

            if response.status_code != 200:
                error_msg = f"API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)

            result = response.json()

            return LLMResponse(
                content=result["content"][0]["text"],
                model=self.model,
                provider="anthropic",
                usage={
                    "input_tokens": result.get("usage", {}).get("input_tokens", 0),
                    "output_tokens": result.get("usage", {}).get("output_tokens", 0)
                },
                finish_reason=result.get("stop_reason"),
                metadata=result
            )

        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            raise

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息

        Returns:
            模型信息字典
        """
        return {
            "provider": "anthropic",
            "model": self.model,
            "supported_models": self.SUPPORTED_MODELS,
            "api_endpoint": self.base_url,
            "capabilities": [
                "chat",
                "function_calling",
                "vision"
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
            response = client.post(
                "/v1/messages",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 10
                }
            )
            return response.status_code in [200, 201]
        except Exception:
            return False

    def __del__(self):
        """清理资源"""
        if self.client:
            self.client.close()


# 注册到工厂
LLMFactory.register_provider("anthropic", AnthropicLLM)
