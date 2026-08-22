# 方案三：更多LLM提供商集成

## 📋 任务概述

- **任务名称**: 集成更多LLM提供商
- **优先级**: 🟡 中
- **难度**: ⭐⭐
- **预计工时**: 20h
- **当前状态**: ⚠️ 仅支持Ollama和OpenAI框架

---

## 🎯 目标

1. 集成Claude API (Anthropic)
2. 集成Gemini API (Google)
3. 实现智能路由和负载均衡
4. 添加模型自动选择策略
5. 统一接口封装

---

## 📊 现有配置分析

### ✅ 已实现

```python
现有支持:
  - OllamaLLM (本地模型)
  - OpenAI (框架存在)
  - ModelManager (模型管理)
```

### ❌ 缺失功能

```python
缺失功能:
  - Claude集成
  - Gemini集成
  - 智能路由
  - 模型选择策略
  - 统一接口
```

---

## 🏗️ 实施方案

### 1. 创建统一接口

```python
# src/core/llm/unified_llm.py

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import logging

class BaseLLM(ABC):
    """LLM统一接口"""

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        pass

    @abstractmethod
    def chat(self, messages: List[Dict], **kwargs) -> str:
        """对话"""
        pass

class LLMFactory:
    """LLM工厂"""

    PROVIDERS = {
        "ollama": OllamaLLM,
        "openai": OpenAILLM,
        "anthropic": AnthropicLLM,  # 新增
        "gemini": GeminiLLM,         # 新增
    }

    @classmethod
    def create(cls, provider: str, config: Dict) -> BaseLLM:
        """创建LLM实例"""
        if provider not in cls.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}")
        return cls.PROVIDERS[provider](config)
```

### 2. Claude集成

```python
# src/core/llm/anthropic_llm.py

import anthropic
from typing import List, Dict

class AnthropicLLM(BaseLLM):
    """Anthropic Claude集成"""

    def __init__(self, config: Dict):
        self.client = anthropic.Anthropic(
            api_key=config["api_key"]
        )
        self.model = config.get("model", "claude-3-5-sonnet-20241022")

    def generate(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=kwargs.get("max_tokens", 1024),
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    def chat(self, messages: List[Dict], **kwargs) -> str:
        """对话"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=kwargs.get("max_tokens", 1024),
            messages=messages
        )
        return response.content[0].text
```

### 3. Gemini集成

```python
# src/core/llm/gemini_llm.py

import google.generativeai as genai
from typing import List, Dict

class GeminiLLM(BaseLLM):
    """Google Gemini集成"""

    def __init__(self, config: Dict):
        genai.configure(api_key=config["api_key"])
        self.model = genai.GenerativeModel(
            model_name=config.get("model", "gemini-1.5-flash")
        )

    def generate(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        response = self.model.generate_content(prompt)
        return response.text

    def chat(self, messages: List[Dict], **kwargs) -> str:
        """对话"""
        chat = self.model.start_chat(history=[])
        for msg in messages:
            response = chat.send_message(msg["content"])
        return response.text
```

---

## ✅ 验收标准

1. ✅ Claude API可正常调用
2. ✅ Gemini API可正常调用
3. ✅ 智能路由正常工作
4. ✅ 统一接口封装完成

是否继续？
