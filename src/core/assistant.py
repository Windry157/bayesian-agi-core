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
from .memory.context_bridge import ContextBridge, context_bridge
from .memory.state_persistence import StatePersistence, state_persistence
from .llm.ollama_service import OllamaLLM
from .learning.learning_manager import LearningManager
from .learning.meta_learning import MetaLearningArchitecture, meta_learning_architecture
from .learning.intrinsic_motivation import IntrinsicMotivationSystem, intrinsic_motivation_system
from .safety.constraint_enforcement import ConstraintEnforcementModule, constraint_enforcement


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
                self.models.append(
                    {"name": model, "provider": "ollama", "type": "local"}
                )

        # 加载OpenAI模型
        openai_provider = providers.get("openai", {})
        if openai_provider.get("enabled", False):
            openai_models = openai_provider.get("models", [])
            for model in openai_models:
                self.models.append(
                    {"name": model, "provider": "openai", "type": "cloud"}
                )

        # 尝试从Ollama API获取模型
        try:
            # 同步获取Ollama模型列表
            ollama_config = {
                "ollama_url": models_config.get("ollama_url", "http://localhost:11434"),
                "default": models_config.get("default", "deepseek-r1:7b"),
            }
            ollama_llm = OllamaLLM(ollama_config)
            # 使用同步方法获取模型列表
            ollama_api_models = ollama_llm.get_available_models_sync()
            for model in ollama_api_models:
                model_name = model["name"]
                # 检查是否已存在
                if not any(m["name"] == model_name for m in self.models):
                    self.models.append(
                        {
                            "name": model_name,
                            "provider": "ollama",
                            "type": "local",
                            "size": model.get("size", 0),
                        }
                    )
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
        self.bayesian_brain = BayesianBrain(
            cognition_coordinator=self.cognition_coordinator
        )
        # 3. 创建系统2（设置贝叶斯大脑）
        self.system2 = System2(bayesian_brain=self.bayesian_brain)
        # 4. 将系统2设置到认知协调器
        self.cognition_coordinator.system2 = self.system2

        self.memory_system = MemorySystem()
        self.learning_manager = LearningManager()
        
        # 新增：持续上下文和认知状态
        self.context_bridge = context_bridge
        self.state_persistence = state_persistence
        
        # 新增：元学习和内在动机系统
        self.meta_learning = meta_learning_architecture
        self.intrinsic_motivation = intrinsic_motivation_system
        
        # 新增：约束执行模块
        self.constraint_enforcement = constraint_enforcement
        
        # 服务和会话管理
        self.services: Dict[str, Any] = {}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

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
        ollama_url = config.get("models", {}).get(
            "ollama_url", "http://localhost:11434"
        )

        # 重新初始化记忆系统，使用配置的向量模型
        self.memory_system = MemorySystem(
            memory_dir=memory_dir, vector_model=vector_model, ollama_url=ollama_url
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
        # 同样清理空metadata
        if metadata == {}:
            metadata = None
        return await self.memory_system.add_memory(content, metadata)

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
    
    async def process_with_context(self, input_text: str, session_id: str) -> Dict[str, Any]:
        """基于完整历史上下文处理
        
        Args:
            input_text: 输入文本
            session_id: 会话ID
            
        Returns:
            处理结果
        """
        try:
            # 1. 加载相关历史上下文
            context = await self.context_bridge.load_relevant_context(session_id, input_text)
            
            # 2. 加载认知状态
            cognitive_state = await self.state_persistence.load_cognitive_state()
            
            # 3. 增强推理
            response = await self._enhanced_reasoning(input_text, context, cognitive_state)
            
            # 4. 约束执行检查
            constraint_result = self.constraint_enforcement.check_constraints(
                input_text, response.get("response", "")
            )
            
            if not constraint_result["passed"]:
                # 使用约束执行模块提供的替代响应
                response["response"] = constraint_result["alternative_response"]
                response["constraint_enforced"] = True
                response["constraint_reason"] = constraint_result["reason"]
            
            # 5. 更新会话上下文
            session_context = {
                "messages": [
                    {"role": "user", "content": input_text, "timestamp": "now"},
                    {"role": "assistant", "content": response.get("response", ""), "timestamp": "now"}
                ],
                "metadata": {"last_input": input_text}
            }
            await self.context_bridge.update_session_context(session_id, session_context)
            
            # 6. 更新认知状态
            await self.state_persistence.update_state(response)
            
            # 7. 记录经验
            experience = {
                "input": input_text,
                "output": response.get("response", ""),
                "context": context,
                "constraint_enforced": response.get("constraint_enforced", False),
                "timestamp": "now"
            }
            await self.learn_from_experience(experience)
            
            return response
            
        except Exception as e:
            logging.error(f"处理上下文失败: {e}")
            return {"error": str(e)}
    
    async def _enhanced_reasoning(self, input_text: str, context: Dict[str, Any], cognitive_state: Dict[str, Any]) -> Dict[str, Any]:
        """增强推理
        
        Args:
            input_text: 输入文本
            context: 上下文信息
            cognitive_state: 认知状态
            
        Returns:
            推理结果
        """
        # 简化实现，实际应该使用更复杂的推理逻辑
        response_text = f"基于上下文的回答: {input_text}"
        
        # 模拟推理结果
        return {
            "response": response_text,
            "context_used": True,
            "cognitive_state_updated": True
        }
    
    async def self_improvement_cycle(self) -> Dict[str, Any]:
        """自我完善循环
        
        Returns:
            改进结果
        """
        try:
            # 调用元学习架构的自我完善循环
            result = await self.meta_learning.self_improvement_cycle()
            
            logging.info("自我完善循环完成")
            return result
            
        except Exception as e:
            logging.error(f"自我完善循环失败: {e}")
            return {"error": str(e)}
    
    async def generate_learning_goals(self) -> List[Dict[str, Any]]:
        """生成学习目标
        
        Returns:
            学习目标列表
        """
        try:
            # 调用内在动机系统生成学习目标
            goals = await self.intrinsic_motivation.generate_learning_goals()
            
            # 转换为字典格式
            goal_dicts = [goal.to_dict() for goal in goals]
            
            logging.info(f"生成学习目标完成: {len(goal_dicts)} 个目标")
            return goal_dicts
            
        except Exception as e:
            logging.error(f"生成学习目标失败: {e}")
            return []
    
    async def start_autonomous_learning(self):
        """启动自主学习
        """
        try:
            # 启动内在动机系统的自主学习循环
            asyncio.create_task(self.intrinsic_motivation.autonomous_learning_loop())
            
            logging.info("自主学习启动成功")
            return True
            
        except Exception as e:
            logging.error(f"启动自主学习失败: {e}")
            return False
    
    def get_system_health(self) -> Dict[str, Any]:
        """获取系统健康状态
        
        Returns:
            系统健康状态
        """
        return {
            "meta_learning": self.meta_learning.get_system_health(),
            "intrinsic_motivation": self.intrinsic_motivation.get_system_status(),
            "cognitive_state": self.state_persistence.get_state_summary(),
            "context_bridge": {
                "session_count": len(self.context_bridge.get_session_contexts())
            }
        }
    
    def clear_session(self, session_id: str):
        """清除会话
        
        Args:
            session_id: 会话ID
        """
        self.context_bridge.clear_session_context(session_id)
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        logging.info(f"清除会话 {session_id}")
    
    def get_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """获取活跃会话
        
        Returns:
            活跃会话
        """
        return self.active_sessions
