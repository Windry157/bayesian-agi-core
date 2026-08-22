#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM模块初始化文件
"""

from .base_llm import (
    LLMFactory,
    LLMRouter,
    LLMPool,
    BaseLLM,
    LLMConfig,
    Message,
    LLMResponse,
    LLMProvider,
    create_llm
)

from .ollama_service import OllamaLLM
from .anthropic_llm import AnthropicLLM
from .gemini_llm import GeminiLLM
from .volcengine_llm import VolcEngineLLM

# 注册提供商
LLMFactory.register_provider("ollama", OllamaLLM)
LLMFactory.register_provider("anthropic", AnthropicLLM)
LLMFactory.register_provider("gemini", GeminiLLM)
LLMFactory.register_provider("volcengine", VolcEngineLLM)
LLMFactory.register_provider("volc", VolcEngineLLM)

__all__ = [
    "LLMFactory",
    "LLMRouter",
    "LLMPool",
    "BaseLLM",
    "LLMConfig",
    "Message",
    "LLMResponse",
    "LLMProvider",
    "create_llm",
    "OllamaLLM",
    "AnthropicLLM",
    "GeminiLLM",
    "VolcEngineLLM"
]