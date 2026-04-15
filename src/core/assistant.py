#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能助理核心模块
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from .interfaces import IModelManager, IAssistant
from .cognition.bayesian_brain import BayesianBrain
from .cognition.cognition_coordinator import CognitionCoordinator
from .cognition.system2 import System2
from .memory.memory_system import MemorySystem
from .llm.ollama_service import OllamaLLM
from .learning.learning_manager import LearningManager


class ModelManager(IModelManager):
    """模型管理器"""
    
    def __init__(self):
        """初始化模型管理器"""
        self.models: List[Dict[str, Any]] = []
    
    def load_from_config(self, config: Dict[str, Any]):
        """从配置加载模型
        
        Args:
            config: 配置
        """
        logging.info(f"开始从配置加载模型列表: {config}")
        models_config = config.get("models", {})
        providers = models_config.get("providers", {})
        
        # 加载Ollama模型
        ollama_provider = providers.get("ollama", {})
        if ollama_provider.get("enabled", True):
            ollama_models = ollama_provider.get("models", [])
            for model in ollama_models:
                self.models.append({
                    "name": model,
                    "provider": "ollama",
                    "type": "local"
                })
        
        # 加载OpenAI模型
        openai_provider = providers.get("openai", {})
        if openai_provider.get("enabled", False):
            openai_models = openai_provider.get("models", [])
            for model in openai_models:
                self.models.append({
                    "name": model,
                    "provider": "openai",
                    "type": "cloud"
                })
        
        # 尝试从Ollama API获取模型
        try:
            # 同步获取Ollama模型列表
            ollama_config = {
                "ollama_url": models_config.get("ollama_url", "http://localhost:11434"),
                "default": models_config.get("default", "deepseek-r1:7b")
            }
            ollama_llm = OllamaLLM(ollama_config)
            # 使用同步方法获取模型列表
            ollama_api_models = ollama_llm.get_available_models_sync()
            for model in ollama_api_models:
                model_name = model["name"]
                # 检查是否已存在
                if not any(m["name"] == model_name for m in self.models):
                    self.models.append({
                        "name": model_name,
                        "provider": "ollama",
                        "type": "local",
                        "size": model.get("size", 0)
                    })
            logging.info(f"从Ollama服务获取到 {len(ollama_api_models)} 个模型")
        except Exception as e:
            logging.error(f"从Ollama服务获取模型列表失败: {e}")
    
    def get_models(self) -> List[Dict[str, Any]]:
        """获取模型列表
        
        Returns:
            模型列表
        """
        return self.models


class Assistant(IAssistant):
    """智能助理"""
    
    def __init__(self):
        """初始化智能助理"""
        self.model_manager = ModelManager()
        
        # 按照正确的顺序初始化，避免循环依赖
        # 1. 创建认知协调器（暂时不设置system2）
        self.cognition_coordinator = CognitionCoordinator()
        # 2. 创建贝叶斯大脑（设置认知协调器）
        self.bayesian_brain = BayesianBrain(cognition_coordinator=self.cognition_coordinator)
        # 3. 创建系统2（设置贝叶斯大脑）
        self.system2 = System2(bayesian_brain=self.bayesian_brain)
        # 4. 将系统2设置到认知协调器
        self.cognition_coordinator.system2 = self.system2
        
        self.memory_system = MemorySystem()
        self.learning_manager = LearningManager()
        self.services: Dict[str, Any] = {}
    
    async def initialize(self, config: Dict[str, Any]):
        """初始化智能助理
        
        Args:
            config: 配置
        """
        # 加载模型
        self.model_manager.load_from_config(config)
        
        # 加载记忆系统配置
        memory_config = config.get("memory", {})
        memory_dir = memory_config.get("directory", "memory")
        vector_model = memory_config.get("vector_model", "ollama:nomic-embed-text")
        ollama_url = config.get("models", {}).get("ollama_url", "http://localhost:11434")
        
        # 重新初始化记忆系统，使用配置的向量模型
        self.memory_system = MemorySystem(
            memory_dir=memory_dir,
            vector_model=vector_model,
            ollama_url=ollama_url
        )
        
        # 加载记忆系统
        await self.memory_system.load()
    
    def register_service(self, name: str, service: Any):
        """注册服务
        
        Args:
            name: 服务名称
            service: 服务实例
        """
        self.services[name] = service
    
    def get_service(self, name: str) -> Optional[Any]:
        """获取服务
        
        Args:
            name: 服务名称
            
        Returns:
            服务实例，如果不存在返回None
        """
        return self.services.get(name)
    
    def get_models(self) -> List[Dict[str, Any]]:
        """获取模型列表
        
        Returns:
            模型列表
        """
        return self.model_manager.get_models()
    
    async def add_memory(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """添加记忆
        
        Args:
            content: 记忆内容
            metadata: 记忆元数据
            
        Returns:
            记忆ID
        """
        # 同样清理空metadata
        if metadata == {}:
            metadata = None
        return await self.memory_system.add_memory(content, metadata)
    
    async def retrieve_memories(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """检索记忆
        
        Args:
            query: 查询内容
            top_k: 返回的记忆数量
            
        Returns:
            检索到的记忆列表
        """
        return await self.memory_system.retrieve_memories(query, top_k)
    
    def update_beliefs(self, evidence: Dict[str, float]):
        """更新信念
        
        Args:
            evidence: 证据
        """
        self.bayesian_brain.update_priors(evidence)
    
    def make_decision(self, possible_actions: List[str]) -> str:
        """做出决策
        
        Args:
            possible_actions: 可能的行动列表
            
        Returns:
            选择的行动
        """
        return self.bayesian_brain.active_inference(possible_actions)
    
    async def learn_from_experience(self, experience: Dict[str, Any]) -> bool:
        """从经验中学习
        
        Args:
            experience: 经验数据，包含交互内容、结果等
            
        Returns:
            是否学习成功
        """
        return await self.learning_manager.learn_from_experience(experience)
    
    def get_learning_history(self) -> List[Dict[str, Any]]:
        """获取学习历史
        
        Returns:
            学习历史列表
        """
        return self.learning_manager.get_learning_history()
    
    def set_learning_rate(self, rate: float):
        """设置学习率
        
        Args:
            rate: 学习率，范围0到1
        """
        self.learning_manager.set_learning_rate(rate)
