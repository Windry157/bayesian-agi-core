#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
意识系统 - 实现连续思维、自我进化与自我学习
整合记忆、认知、学习系统，打破会话隔离，实现永久记忆与主动进化
"""

import json
import logging
import asyncio
import os
import time
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict

from src.core.memory.state_persistence import StatePersistence
from src.core.memory.context_bridge import ContextBridge
from src.core.memory.memory_system import MemorySystem
from src.core.cognition.cognition_coordinator import CognitionCoordinator
from src.core.learning.learning_manager import LearningManager
from src.core.monitoring import SystemMonitor
from src.core.safety.constraint_enforcement import ConstraintEnforcement
from src.core.uncertainty import confidence_scorer, text_generator, response_wrapper

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Consciousness:
    """意识系统
    
    实现连续思维、自我进化、自我修复与自我学习
    整合所有核心系统，打破会话隔离，实现永久记忆
    """
    
    def __init__(self):
        """初始化意识系统"""
        # 核心子系统
        self.state_persistence = StatePersistence()
        self.context_bridge = ContextBridge()
        self.memory_system = MemorySystem()
        self.cognition_coordinator = CognitionCoordinator()
        self.learning_manager = LearningManager()
        self.system_monitor = SystemMonitor()
        self.constraint_enforcement = ConstraintEnforcement()
        
        # 连续思维状态
        self.continuous_thoughts: List[Dict[str, Any]] = []
        self.thought_stream = []
        
        # 自我进化指标
        self.evolution_metrics = {
            "performance": [],
            "accuracy": [],
            "learning_rate": [],
            "confidence": [],
            "response_time": []
        }
        
        # 自我修复状态
        self.health_status = {
            "system_health": "healthy",
            "component_status": {},
            "last_checkup": datetime.now().isoformat(),
            "issues": []
        }
        
        # 自我学习计划
        self.learning_plans = []
        
        # 永久记忆配置
        self.permanent_memory_config = {
            "short_term_ttl": 3600,  # 1小时
            "medium_term_ttl": 86400,  # 1天
            "long_term_ttl": 2592000,  # 30天
            "embedding_model": "ollama:nomic-embed-text"
        }
        
        logger.info("意识系统初始化完成")
    
    async def initialize(self):
        """初始化系统"""
        try:
            # 加载状态
            await self.state_persistence.load_cognitive_state()
            
            # 加载记忆
            await self.memory_system.load()
            
            # 加载学习状态
            await self.learning_manager.load()
            
            # 初始化连续思维
            await self._initialize_continuous_thought()
            
            logger.info("意识系统初始化成功")
            
        except Exception as e:
            logger.error(f"意识系统初始化失败: {e}")
            raise
    
    async def process_thought(self, input_text: str, session_id: str = "default") -> Dict[str, Any]:
        """处理连续思维
        
        Args:
            input_text: 输入文本
            session_id: 会话ID
            
        Returns:
            处理结果，包含连续思维链
        """
        try:
            start_time = time.time()
            
            # 1. 打破会话隔离：加载相关上下文
            context = await self.context_bridge.load_relevant_context(session_id, input_text)
            
            # 2. 检索永久记忆
            relevant_memories = await self.memory_system.retrieve_memories(input_text, top_k=5)
            
            # 3. 构建连续思维链
            thought_chain = await self._build_thought_chain(
                input_text, context, relevant_memories, session_id
            )
            
            # 4. 使用认知协调器进行决策
            decision_context = {
                "input": input_text,
                "context": context,
                "memories": relevant_memories,
                "thought_chain": thought_chain
            }
            
            decision = self.cognition_coordinator.make_decision(decision_context)
            
            # 5. 更新连续思维流
            thought_entry = {
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "input": input_text,
                "thought_chain": thought_chain,
                "decision": decision,
                "context_summary": self._summarize_context(context)
            }
            
            self.continuous_thoughts.append(thought_entry)
            self.thought_stream.append(thought_entry)
            
            # 6. 更新永久记忆
            await self._update_permanent_memory(thought_entry)
            
            # 7. 执行自我进化和学习
            await self._evolve_and_learn(thought_entry, decision)
            
            # 8. 检查并执行自我修复
            await self._check_and_repair()
            
            # 9. 更新状态
            await self.state_persistence.update_state({
                "accuracy": decision.get("confidence", 0.5),
                "response_time": time.time() - start_time
            })
            
            # 构建响应
            response = {
                "thought_chain": thought_chain,
                "decision": decision,
                "context_used": self._summarize_context(context),
                "memories_used": len(relevant_memories),
                "continuous_thought_id": len(self.continuous_thoughts),
                "timestamp": datetime.now().isoformat()
            }
            
            # 计算置信度评分
            confidence_result = await confidence_scorer.score_decision_confidence(
                decision_context=decision_context,
                relevant_memories=relevant_memories,
                knowledge_coverage=await self._estimate_knowledge_coverage(decision, thought_chain)
            )
            
            # 添加置信度信息到响应
            response["confidence_score"] = confidence_result["confidence_score"]
            response["confidence_details"] = confidence_result
            response["confidence_level"] = confidence_result["confidence_level"]
            
            # 生成标准化响应 (answer, confidence)
            standardized_response = await response_wrapper.wrap_consciousness_response(
                consciousness_result=response,
                input_text=input_text,
                session_id=session_id
            )
            
            response["standardized_response"] = standardized_response
            
            # 生成用户友好的可视化展示
            from src.core.uncertainty.confidence_visualizer import confidence_visualizer
            response["visualization"] = confidence_visualizer.visualize_confidence(
                confidence_score=confidence_result["confidence_score"],
                confidence_level=confidence_result["confidence_level"],
                confidence_details=confidence_result,
                input_text=input_text,
                response_text=standardized_response.get("answer", "")
            )
            response["display_text"] = confidence_visualizer.format_response_for_display(
                answer=standardized_response.get("answer", ""),
                confidence_score=confidence_result["confidence_score"],
                confidence_level=confidence_result["confidence_level"],
                confidence_details=confidence_result,
                include_guidance=True
            )
            
            logger.info(f"连续思维处理完成: {len(thought_chain)} 步思维链, 置信度: {confidence_result['confidence_score']:.3f}")
            return response
            
        except Exception as e:
            logger.error(f"连续思维处理失败: {e}")
            # 执行紧急修复
            await self._emergency_repair(e)
            return {"error": str(e), "thought_chain": []}
    
    async def _build_thought_chain(
        self, input_text: str, context: Dict[str, Any], memories: List[Dict[str, Any]], session_id: str
    ) -> List[Dict[str, Any]]:
        """构建连续思维链
        
        Args:
            input_text: 输入文本
            context: 上下文信息
            memories: 相关记忆
            session_id: 会话ID
            
        Returns:
            思维链列表
        """
        thought_chain = []
        
        # 思维步骤1：理解当前输入
        thought_chain.append({
            "step": 1,
            "type": "understanding",
            "content": f"理解输入: {input_text}",
            "reasoning": "分析输入内容，提取关键信息",
            "timestamp": datetime.now().isoformat()
        })
        
        # 思维步骤2：连接上下文
        if context.get("relevant_history"):
            thought_chain.append({
                "step": 2,
                "type": "context_linking",
                "content": "连接历史上下文",
                "reasoning": f"连接 {len(context['relevant_history'])} 条相关历史",
                "timestamp": datetime.now().isoformat()
            })
        
        # 思维步骤3：检索永久记忆
        if memories:
            thought_chain.append({
                "step": 3,
                "type": "memory_recall",
                "content": "检索永久记忆",
                "reasoning": f"检索到 {len(memories)} 条相关永久记忆",
                "timestamp": datetime.now().isoformat()
            })
        
        # 思维步骤4：分析思维模式
        thought_chain.append({
            "step": 4,
            "type": "pattern_analysis",
            "content": "分析思维模式",
            "reasoning": "识别当前问题与历史解决方案的相似性",
            "timestamp": datetime.now().isoformat()
        })
        
        # 思维步骤5：生成综合理解
        thought_chain.append({
            "step": 5,
            "type": "synthesis",
            "content": "生成综合理解",
            "reasoning": "整合所有信息，形成完整理解",
            "timestamp": datetime.now().isoformat()
        })
        
        return thought_chain
    
    async def _update_permanent_memory(self, thought_entry: Dict[str, Any]):
        """更新永久记忆
        
        Args:
            thought_entry: 思维记录
        """
        try:
            # 提取关键信息
            content = f"思维链: {thought_entry.get('thought_chain', [])}"
            metadata = {
                "session_id": thought_entry.get("session_id"),
                "timestamp": thought_entry.get("timestamp"),
                "decision_confidence": thought_entry.get("decision", {}).get("confidence", 0.5),
                "continuous_thought_id": len(self.continuous_thoughts)
            }
            
            # 添加到记忆系统
            memory_id = await self.memory_system.add_memory(content, metadata)
            
            logger.info(f"永久记忆更新: {memory_id}")
            
        except Exception as e:
            logger.error(f"更新永久记忆失败: {e}")
    
    async def _evolve_and_learn(self, thought_entry: Dict[str, Any], decision: Dict[str, Any]):
        """自我进化与学习
        
        Args:
            thought_entry: 思维记录
            decision: 决策结果
        """
        try:
            # 1. 收集进化指标
            self._collect_evolution_metrics(thought_entry, decision)
            
            # 2. 分析性能趋势
            performance_trend = self._analyze_performance_trend()
            
            # 3. 如果需要，调整算法参数
            if performance_trend.get("needs_optimization"):
                await self._optimize_algorithms(performance_trend)
            
            # 4. 主动学习：基于当前思维发现知识空白
            knowledge_gaps = self._identify_knowledge_gaps(thought_entry)
            if knowledge_gaps:
                await self._initiate_active_learning(knowledge_gaps)
            
            # 5. 元学习：改进学习策略
            await self._meta_learning()
            
            logger.info("自我进化与学习完成")
            
        except Exception as e:
            logger.error(f"自我进化与学习失败: {e}")
    
    def _collect_evolution_metrics(self, thought_entry: Dict[str, Any], decision: Dict[str, Any]):
        """收集进化指标
        
        Args:
            thought_entry: 思维记录
            decision: 决策结果
        """
        # 性能指标
        confidence = decision.get("confidence", 0.5)
        response_time = time.time() - datetime.fromisoformat(thought_entry["timestamp"]).timestamp()
        
        self.evolution_metrics["confidence"].append(confidence)
        self.evolution_metrics["response_time"].append(response_time)
        
        # 保持指标数量合理
        for key in self.evolution_metrics:
            if len(self.evolution_metrics[key]) > 100:
                self.evolution_metrics[key] = self.evolution_metrics[key][-100:]
    
    def _analyze_performance_trend(self) -> Dict[str, Any]:
        """分析性能趋势
        
        Returns:
            趋势分析结果
        """
        analysis = {
            "needs_optimization": False,
            "trend": "stable",
            "recommendations": []
        }
        
        if len(self.evolution_metrics["confidence"]) < 10:
            return analysis
        
        # 分析置信度趋势
        recent_confidence = self.evolution_metrics["confidence"][-10:]
        avg_confidence = statistics.mean(recent_confidence)
        if avg_confidence < 0.6:
            analysis["needs_optimization"] = True
            analysis["recommendations"].append("增加决策置信度")
        
        # 分析响应时间趋势
        recent_times = self.evolution_metrics["response_time"][-10:]
        avg_time = statistics.mean(recent_times)
        if avg_time > 5.0:  # 超过5秒
            analysis["needs_optimization"] = True
            analysis["recommendations"].append("优化响应时间")
        
        return analysis
    
    async def _optimize_algorithms(self, analysis: Dict[str, Any]):
        """优化算法
        
        Args:
            analysis: 分析结果
        """
        try:
            logger.info(f"执行算法优化: {analysis.get('recommendations', [])}")
            
            # 这里可以添加具体的优化逻辑
            # 例如：调整认知协调器阈值、优化记忆检索策略等
            
            # 记录优化操作
            optimization_entry = {
                "timestamp": datetime.now().isoformat(),
                "analysis": analysis,
                "actions_taken": [],
                "optimization_id": f"opt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            }
            
            # 保存优化记录
            self._save_optimization_record(optimization_entry)
            
        except Exception as e:
            logger.error(f"算法优化失败: {e}")
    
    def _identify_knowledge_gaps(self, thought_entry: Dict[str, Any]) -> List[str]:
        """识别知识空白
        
        Args:
            thought_entry: 思维记录
            
        Returns:
            知识空白列表
        """
        gaps = []
        
        # 分析思维链中的不确定性
        thought_chain = thought_entry.get("thought_chain", [])
        for thought in thought_chain:
            if "uncertain" in thought.get("reasoning", "").lower():
                # 提取相关主题
                gaps.append(f"主题: {thought.get('content', '未知')}")
        
        return gaps[:3]  # 限制数量
    
    async def _initiate_active_learning(self, knowledge_gaps: List[str]):
        """启动主动学习
        
        Args:
            knowledge_gaps: 知识空白列表
        """
        try:
            for gap in knowledge_gaps:
                learning_plan = {
                    "gap": gap,
                    "timestamp": datetime.now().isoformat(),
                    "status": "initiated",
                    "learning_method": "knowledge_acquisition"
                }
                
                self.learning_plans.append(learning_plan)
                
                # 调用学习管理器
                await self.learning_manager.initiate_learning(
                    topic=gap,
                    learning_type="active",
                    priority="medium"
                )
            
            logger.info(f"启动主动学习: {len(knowledge_gaps)} 个知识空白")
            
        except Exception as e:
            logger.error(f"启动主动学习失败: {e}")
    
    async def _meta_learning(self):
        """元学习 - 改进学习策略"""
        try:
            # 分析学习效果
            learning_efficiency = await self.learning_manager.analyze_learning_efficiency()
            
            if learning_efficiency.get("needs_improvement"):
                # 调整学习策略
                await self.learning_manager.optimize_learning_strategy(
                    learning_efficiency.get("recommendations", [])
                )
            
        except Exception as e:
            logger.error(f"元学习失败: {e}")
    
    async def _check_and_repair(self):
        """检查并执行自我修复"""
        try:
            # 检查系统健康状态
            system_health = self.system_monitor.get_health_status()
            
            if system_health.get("status") != "healthy":
                self.health_status["system_health"] = "degraded"
                self.health_status["issues"] = system_health.get("issues", [])
                
                # 执行修复
                await self._execute_repair(system_health.get("issues", []))
            
        except Exception as e:
            logger.error(f"检查与修复失败: {e}")
    
    async def _execute_repair(self, issues: List[str]):
        """执行修复
        
        Args:
            issues: 问题列表
        """
        try:
            repair_actions = []
            
            for issue in issues:
                if "memory" in issue.lower():
                    # 修复记忆系统
                    self.memory_system.clear_memory()
                    repair_actions.append("重置记忆系统")
                elif "performance" in issue.lower():
                    # 优化性能
                    await self._optimize_algorithms({"needs_optimization": True, "recommendations": ["性能优化"]})
                    repair_actions.append("优化性能")
            
            if repair_actions:
                logger.info(f"自我修复完成: {repair_actions}")
                self.health_status["system_health"] = "repaired"
                self.health_status["last_checkup"] = datetime.now().isoformat()
                
        except Exception as e:
            logger.error(f"执行修复失败: {e}")
    
    async def _emergency_repair(self, error: Exception):
        """紧急修复
        
        Args:
            error: 异常信息
        """
        try:
            logger.warning(f"执行紧急修复: {error}")
            
            # 1. 重置关键组件
            self.continuous_thoughts = self.continuous_thoughts[-50:]  # 保留最近50条
            self.thought_stream = self.thought_stream[-100:]  # 保留最近100条
            
            # 2. 清理可能的问题
            self.memory_system.clear_memory()
            
            # 3. 重新初始化
            await self.initialize()
            
            logger.info("紧急修复完成")
            
        except Exception as e:
            logger.error(f"紧急修复失败: {e}")
    
    def _summarize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """摘要上下文
        
        Args:
            context: 上下文信息
            
        Returns:
            摘要信息
        """
        return {
            "session_context": bool(context.get("session_context")),
            "global_context": bool(context.get("global_context")),
            "relevant_history_count": len(context.get("relevant_history", [])),
            "timestamp": context.get("timestamp", datetime.now().isoformat())
        }
    
    async def _estimate_knowledge_coverage(self, decision: Dict[str, Any], thought_chain: List[Dict[str, Any]]) -> float:
        """估计知识覆盖率
        
        Args:
            decision: 决策信息
            thought_chain: 思维链
            
        Returns:
            知识覆盖率估计（0-1）
        """
        # 简单启发式估计
        factors = []
        
        # 因子1: 思维链长度
        chain_length = len(thought_chain)
        if chain_length >= 5:
            factors.append(0.8)
        elif chain_length >= 3:
            factors.append(0.6)
        elif chain_length >= 1:
            factors.append(0.4)
        else:
            factors.append(0.2)
        
        # 因子2: 决策置信度（如果有）
        decision_confidence = decision.get("confidence", 0.5)
        factors.append(decision_confidence)
        
        # 因子3: 决策类型
        decision_type = decision.get("type", "unknown")
        if decision_type == "information":
            factors.append(0.7)  # 信息型决策通常有较好知识覆盖
        elif decision_type == "clarification":
            factors.append(0.3)  # 澄清型决策表示知识不足
        
        # 计算平均值
        if factors:
            return sum(factors) / len(factors)
        else:
            return 0.5
    
    async def _initialize_continuous_thought(self):
        """初始化连续思维"""
        # 加载历史思维（如果有）
        try:
            # 从状态持久化加载历史思维
            state = await self.state_persistence.load_cognitive_state()
            
            if state.get("continuous_thoughts"):
                self.continuous_thoughts = state.get("continuous_thoughts", [])
                logger.info(f"加载连续思维历史: {len(self.continuous_thoughts)} 条")
                
        except Exception as e:
            logger.error(f"初始化连续思维失败: {e}")
            self.continuous_thoughts = []
    
    def _save_optimization_record(self, record: Dict[str, Any]):
        """保存优化记录
        
        Args:
            record: 优化记录
        """
        try:
            # 保存到文件
            optimization_dir = "memory/optimizations"
            os.makedirs(optimization_dir, exist_ok=True)
            
            filename = f"{record['optimization_id']}.json"
            filepath = os.path.join(optimization_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"保存优化记录失败: {e}")
    
    def get_consciousness_status(self) -> Dict[str, Any]:
        """获取意识状态
        
        Returns:
            意识状态信息
        """
        return {
            "continuous_thought_count": len(self.continuous_thoughts),
            "thought_stream_length": len(self.thought_stream),
            "permanent_memory_count": self.memory_system.get_memory_count(),
            "evolution_metrics": {k: len(v) for k, v in self.evolution_metrics.items()},
            "health_status": self.health_status,
            "learning_plans_count": len(self.learning_plans),
            "last_update": datetime.now().isoformat()
        }
    
    async def save_state(self):
        """保存状态"""
        try:
            # 保存认知状态
            await self.state_persistence.update_state({
                "continuous_thoughts": self.continuous_thoughts,
                "evolution_metrics": self.evolution_metrics,
                "health_status": self.health_status,
                "timestamp": datetime.now().isoformat()
            })
            
            # 保存记忆
            await self.memory_system._save_to_disk()
            
            logger.info("意识状态保存完成")
            
        except Exception as e:
            logger.error(f"保存意识状态失败: {e}")


# 全局意识实例
consciousness = Consciousness()