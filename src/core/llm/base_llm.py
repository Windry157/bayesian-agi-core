#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一LLM接口模块
提供多种LLM提供商的统一接口

支持：
- Ollama（本地模型）
- OpenAI
- Anthropic (Claude)
- Google (Gemini)

设计原则：
- 抽象基类定义统一接口
- 工厂模式创建实例
- 策略模式支持动态切换
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass
from enum import Enum
import os

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """LLM提供商枚举"""
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    VOLCENGINE = "volcengine"


@dataclass
class LLMConfig:
    """LLM配置"""
    provider: str
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 60
    retry_attempts: int = 3
    stream: bool = False


@dataclass
class Message:
    """对话消息"""
    role: str
    content: str
    name: Optional[str] = None


@dataclass
class LLMResponse:
    """LLM响应"""
    content: str
    model: str
    provider: str
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseLLM(ABC):
    """LLM统一抽象基类

    所有LLM实现必须继承此类并实现以下方法：
    - generate()
    - chat()
    - get_model_info()
    """

    def __init__(self, config: LLMConfig):
        """初始化LLM

        Args:
            config: LLM配置
        """
        self.config = config
        self.provider = config.provider
        self.model = config.model

    @abstractmethod
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
            LLMResponse: 生成的响应
        """
        pass

    @abstractmethod
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
            LLMResponse: 生成的响应
        """
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息

        Returns:
            模型信息字典
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查模型是否可用

        Returns:
            是否可用
        """
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} provider={self.provider} model={self.model}>"


class LLMFactory:
    """LLM工厂类

    统一创建LLM实例的工厂。
    """

    _providers: Dict[str, type] = {}

    @classmethod
    def register_provider(cls, name: str, provider_class: type):
        """注册LLM提供商

        Args:
            name: 提供商名称
            provider_class: 提供商类
        """
        cls._providers[name] = provider_class
        logger.info(f"Registered LLM provider: {name}")

    @classmethod
    def create(cls, config: Union[LLMConfig, Dict[str, Any]]) -> BaseLLM:
        """创建LLM实例

        Args:
            config: LLM配置

        Returns:
            LLM实例

        Raises:
            ValueError: 不支持的提供商
        """
        if isinstance(config, dict):
            config = LLMConfig(**config)

        provider_name = config.provider.lower()

        if provider_name not in cls._providers:
            raise ValueError(
                f"Unknown provider: {provider_name}. "
                f"Available: {list(cls._providers.keys())}"
            )

        provider_class = cls._providers[provider_name]
        return provider_class(config)

    @classmethod
    def create_from_env(cls, provider: str, model: str) -> BaseLLM:
        """从环境变量创建LLM实例

        Args:
            provider: 提供商名称
            model: 模型名称

        Returns:
            LLM实例
        """
        config = LLMConfig(
            provider=provider,
            model=model,
            api_key=os.getenv(f"{provider.upper()}_API_KEY"),
            base_url=os.getenv(f"{provider.upper()}_BASE_URL")
        )
        return cls.create(config)

    @classmethod
    def get_available_providers(cls) -> List[str]:
        """获取可用的提供商列表

        Returns:
            提供商名称列表
        """
        return list(cls._providers.keys())


class LLMRouter:
    """LLM路由器

    支持多种负载均衡和故障转移策略。
    """

    def __init__(self):
        """初始化路由器"""
        self.providers: List[BaseLLM] = []
        self.current_index = 0

    def add_provider(self, llm: BaseLLM, weight: int = 1):
        """添加LLM提供商

        Args:
            llm: LLM实例
            weight: 权重
        """
        for _ in range(weight):
            self.providers.append(llm)

    def get_next(self) -> Optional[BaseLLM]:
        """获取下一个可用的LLM（轮询）

        Returns:
            LLM实例，如果都不可用返回None
        """
        if not self.providers:
            return None

        attempts = 0
        max_attempts = len(self.providers)

        while attempts < max_attempts:
            llm = self.providers[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.providers)

            if llm.is_available():
                return llm

            attempts += 1

        return None

    def get_by_model(self, model: str) -> Optional[BaseLLM]:
        """根据模型名称获取LLM

        Args:
            model: 模型名称

        Returns:
            LLM实例，如果不存在返回None
        """
        for llm in self.providers:
            if llm.model == model:
                return llm
        return None

    def get_by_provider(self, provider: str) -> List[BaseLLM]:
        """根据提供商获取所有LLM

        Args:
            provider: 提供商名称

        Returns:
            LLM实例列表
        """
        return [
            llm for llm in self.providers
            if llm.provider == provider
        ]

    def get_all_healthy(self) -> List[BaseLLM]:
        """获取所有健康的LLM

        Returns:
            LLM实例列表
        """
        return [
            llm for llm in self.providers
            if llm.is_available()
        ]

    def get_best(self, criteria: Callable[[BaseLLM], float] = None) -> Optional[BaseLLM]:
        """获取最佳LLM

        Args:
            criteria: 评分函数

        Returns:
            最佳LLM实例
        """
        healthy = self.get_all_healthy()

        if not healthy:
            return None

        if criteria is None:
            # 默认返回第一个
            return healthy[0]

        # 按评分排序
        scored = [(llm, criteria(llm)) for llm in healthy]
        scored.sort(key=lambda x: x[1], reverse=True)

        return scored[0][0] if scored else None


class LLMPool:
    """LLM连接池

    管理多个LLM实例，支持自动故障转移和负载均衡。
    """

    def __init__(self, router: Optional[LLMRouter] = None):
        """初始化连接池

        Args:
            router: LLM路由器
        """
        self.router = router or LLMRouter()
        self.fallback_llm: Optional[BaseLLM] = None

    def set_fallback(self, llm: BaseLLM):
        """设置备用LLM

        Args:
            llm: 备用LLM
        """
        self.fallback_llm = llm

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        use_router: bool = True,
        **kwargs
    ) -> LLMResponse:
        """生成文本

        Args:
            prompt: 提示词
            model: 指定模型
            use_router: 是否使用路由器
            **kwargs: 其他参数

        Returns:
            LLMResponse
        """
        llm = None

        if model and not use_router:
            llm = self.router.get_by_model(model)
        elif use_router:
            llm = self.router.get_next()

        if llm is None and self.fallback_llm:
            llm = self.fallback_llm
            logger.warning("Using fallback LLM")

        if llm is None:
            raise ValueError("No available LLM provider")

        return llm.generate(prompt, **kwargs)

    def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        use_router: bool = True,
        **kwargs
    ) -> LLMResponse:
        """对话

        Args:
            messages: 消息列表
            model: 指定模型
            use_router: 是否使用路由器
            **kwargs: 其他参数

        Returns:
            LLMResponse
        """
        llm = None

        if model and not use_router:
            llm = self.router.get_by_model(model)
        elif use_router:
            llm = self.router.get_next()

        if llm is None and self.fallback_llm:
            llm = self.fallback_llm
            logger.warning("Using fallback LLM")

        if llm is None:
            raise ValueError("No available LLM provider")

        return llm.chat(messages, **kwargs)

    def add_provider(self, llm: BaseLLM, weight: int = 1):
        """添加提供商到池

        Args:
            llm: LLM实例
            weight: 权重
        """
        self.router.add_provider(llm, weight)


# 便捷函数
def create_llm(
    provider: str,
    model: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    **kwargs
) -> BaseLLM:
    """便捷函数：创建LLM实例

    Args:
        provider: 提供商名称
        model: 模型名称
        api_key: API密钥
        base_url: API基础URL
        **kwargs: 其他配置

    Returns:
        LLM实例
    """
    config = LLMConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
        **kwargs
    )
    return LLMFactory.create(config)
