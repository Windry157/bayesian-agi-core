#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心组件接口定义
"""

from abc import ABC, abstractmethod
from typing import List, Dict, AsyncGenerator, Any, Optional


class IBayesianBrain(ABC):
    """贝叶斯大脑接口"""

    @abstractmethod
    def update_priors(self, new_evidence: Dict[str, float]):
        """更新先验概率

        Args:
            new_evidence: 新的证据，键为状态，值为概率
        """
        pass

    @abstractmethod
    def bayesian_update(self, observation: Dict) -> Dict[str, float]:
        """执行贝叶斯更新

        Args:
            observation: 当前观测

        Returns:
            更新后的后验概率
        """
        pass

    @abstractmethod
    def active_inference(self, possible_actions: List[str]) -> str:
        """主动推理选择行动

        Args:
            possible_actions: 可能的行动列表

        Returns:
            选择的行动
        """
        pass

    @abstractmethod
    def get_beliefs(self) -> Dict[str, float]:
        """获取当前信念状态

        Returns:
            当前世界模型的概率分布
        """
        pass

    @abstractmethod
    def reset(self):
        """重置贝叶斯大脑"""
        pass


class IMemorySystem(ABC):
    """记忆系统接口"""

    @abstractmethod
    async def add_memory(
        self, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """添加记忆

        Args:
            content: 记忆内容
            metadata: 记忆元数据

        Returns:
            记忆ID
        """
        pass

    @abstractmethod
    async def retrieve_memories(
        self, query: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """检索记忆

        Args:
            query: 查询内容
            top_k: 返回的记忆数量

        Returns:
            检索到的记忆列表
        """
        pass

    @abstractmethod
    async def get_knowledge_graph(self) -> Dict[str, Any]:
        """获取知识图谱

        Returns:
            知识图谱数据
        """
        pass

    @abstractmethod
    async def add_entity(self, entity_id: str, properties: Dict[str, Any]) -> bool:
        """添加实体

        Args:
            entity_id: 实体ID
            properties: 实体属性

        Returns:
            是否添加成功
        """
        pass

    @abstractmethod
    async def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """添加关系

        Args:
            source_id: 源实体ID
            target_id: 目标实体ID
            relation_type: 关系类型
            properties: 关系属性

        Returns:
            是否添加成功
        """
        pass

    @abstractmethod
    async def save(self):
        """保存记忆系统"""
        pass

    @abstractmethod
    async def load(self):
        """加载记忆系统"""
        pass


class ILLMService(ABC):
    """LLM服务接口"""

    @abstractmethod
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
        pass

    @abstractmethod
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """获取可用模型

        Returns:
            模型列表
        """
        pass

    @abstractmethod
    def get_available_models_sync(self) -> List[Dict[str, Any]]:
        """同步获取可用模型

        Returns:
            模型列表
        """
        pass


class IModelManager(ABC):
    """模型管理器接口"""

    @abstractmethod
    def load_from_config(self, config: Dict[str, Any]):
        """从配置加载模型

        Args:
            config: 配置
        """
        pass

    @abstractmethod
    def get_models(self) -> List[Dict[str, Any]]:
        """获取模型列表

        Returns:
            模型列表
        """
        pass


class IAssistant(ABC):
    """智能助理接口"""

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]):
        """初始化智能助理

        Args:
            config: 配置
        """
        pass

    @abstractmethod
    def register_service(self, name: str, service: Any):
        """注册服务

        Args:
            name: 服务名称
            service: 服务实例
        """
        pass

    @abstractmethod
    def get_service(self, name: str) -> Optional[Any]:
        """获取服务

        Args:
            name: 服务名称

        Returns:
            服务实例，如果不存在返回None
        """
        pass

    @abstractmethod
    def get_models(self) -> List[Dict[str, Any]]:
        """获取模型列表

        Returns:
            模型列表
        """
        pass

    @abstractmethod
    async def add_memory(
        self, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """添加记忆

        Args:
            content: 记忆内容
            metadata: 记忆元数据

        Returns:
            记忆ID
        """
        pass

    @abstractmethod
    async def retrieve_memories(
        self, query: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """检索记忆

        Args:
            query: 查询内容
            top_k: 返回的记忆数量

        Returns:
            检索到的记忆列表
        """
        pass

    @abstractmethod
    def update_beliefs(self, evidence: Dict[str, float]):
        """更新信念

        Args:
            evidence: 证据
        """
        pass

    @abstractmethod
    def make_decision(self, possible_actions: List[str]) -> str:
        """做出决策

        Args:
            possible_actions: 可能的行动列表

        Returns:
            选择的行动
        """
        pass
