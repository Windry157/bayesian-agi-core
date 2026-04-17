#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习管理器
负责管理系统的自主学习过程
"""

import logging
import asyncio
from datetime import datetime
from typing import List, Tuple, Dict, Any
from ..knowledge import knowledge_graph

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class LearningManager:
    """学习管理器"""

    def __init__(self):
        """初始化学习管理器"""
        self.learning_history = []
        self.learning_rate = 0.1  # 学习率
        logger.info("学习管理器初始化完成")

    async def learn_from_experience(self, experience):
        """从经验中学习

        Args:
            experience: 经验数据，包含交互内容、结果等
        """
        try:
            logger.info(f"开始从经验中学习: {experience}")

            # 1. 提取经验中的关键信息
            key_information = self._extract_key_information(experience)

            # 2. 更新知识图谱
            await self._update_knowledge_graph(key_information)

            # 3. 优化决策模型
            await self._optimize_decision_model(experience)

            # 4. 记录学习历史
            self._record_learning_history(experience, key_information)

            logger.info("从经验中学习完成")
            return True
        except Exception as e:
            logger.error(f"学习过程中发生错误: {e}")
            return False

    def _extract_key_information(self, experience):
        """提取经验中的关键信息

        Args:
            experience: 经验数据

        Returns:
            提取的关键信息
        """
        # 这里可以实现更复杂的信息提取逻辑
        key_information = {
            "timestamp": datetime.now().isoformat(),
            "input": experience.get("input", ""),
            "output": experience.get("output", ""),
            "feedback": experience.get("feedback", 0),  # 反馈分数，范围-1到1
            "context": experience.get("context", {}),
        }
        return key_information

    async def _update_knowledge_graph(self, key_information):
        """更新知识图谱

        Args:
            key_information: 关键信息
        """
        logger.info("更新知识图谱")
        
        # 提取文本信息
        input_text = key_information.get("input", "")
        output_text = key_information.get("output", "")
        context = key_information.get("context", {})
        
        # 从输入文本中提取实体
        input_entities = await knowledge_graph.extract_entities(input_text)
        
        # 从输出文本中提取实体
        output_entities = await knowledge_graph.extract_entities(output_text)
        
        # 合并实体
        all_entities = input_entities + output_entities
        
        # 添加实体到知识图谱
        for entity_name, entity_type in all_entities:
            entity_id = f"{entity_type}:{entity_name}"
            await knowledge_graph.add_entity(
                entity_id=entity_id,
                entity_type=entity_type,
                properties={"name": entity_name, "source": "learning"}
            )
        
        # 提取关系
        if all_entities:
            input_relations = await knowledge_graph.extract_relations(input_text, all_entities)
            output_relations = await knowledge_graph.extract_relations(output_text, all_entities)
            
            # 添加关系到知识图谱
            for subject_name, predicate, object_name in input_relations + output_relations:
                subject_id = f"{self._get_entity_type(subject_name, all_entities)}:{subject_name}"
                object_id = f"{self._get_entity_type(object_name, all_entities)}:{object_name}"
                await knowledge_graph.add_relation(
                    subject=subject_id,
                    predicate=predicate,
                    object_=object_id,
                    properties={"source": "learning"}
                )
        
        # 记录知识图谱统计信息
        stats = knowledge_graph.get_statistics()
        logger.info(f"知识图谱更新完成: {stats}")
    
    def _get_entity_type(self, entity_name: str, entities: List[Tuple[str, str]]) -> str:
        """获取实体类型

        Args:
            entity_name: 实体名称
            entities: 实体列表

        Returns:
            实体类型
        """
        for name, entity_type in entities:
            if name == entity_name:
                return entity_type
        return "unknown"

    async def _optimize_decision_model(self, experience):
        """优化决策模型

        Args:
            experience: 经验数据
        """
        # 这里可以实现决策模型的优化逻辑
        # 例如，根据反馈调整决策权重
        logger.info("优化决策模型")
        # 模拟优化过程
        await asyncio.sleep(0.1)

    def _record_learning_history(self, experience, key_information):
        """记录学习历史

        Args:
            experience: 经验数据
            key_information: 提取的关键信息
        """
        learning_record = {
            "timestamp": datetime.now().isoformat(),
            "experience": experience,
            "key_information": key_information,
        }
        self.learning_history.append(learning_record)
        # 限制历史记录长度，防止内存占用过高
        if len(self.learning_history) > 1000:
            self.learning_history = self.learning_history[-1000:]

    def get_learning_history(self):
        """获取学习历史

        Returns:
            学习历史列表
        """
        return self.learning_history

    def set_learning_rate(self, rate):
        """设置学习率

        Args:
            rate: 学习率，范围0到1
        """
        if 0 <= rate <= 1:
            self.learning_rate = rate
            logger.info(f"学习率设置为: {rate}")
        else:
            logger.error("学习率必须在0到1之间")
    
    async def load(self):
        """加载学习状态"""
        try:
            # 这里可以加载持久化的学习状态
            logger.info("学习状态加载完成")
        except Exception as e:
            logger.error(f"加载学习状态失败: {e}")
    
    async def initiate_learning(self, topic: str, learning_type: str = "active", priority: str = "medium"):
        """启动学习
        
        Args:
            topic: 学习主题
            learning_type: 学习类型（主动/被动）
            priority: 优先级
            
        Returns:
            学习是否成功启动
        """
        try:
            logger.info(f"启动{learning_type}学习: {topic} (优先级: {priority})")
            
            # 创建学习记录
            learning_record = {
                "topic": topic,
                "type": learning_type,
                "priority": priority,
                "timestamp": datetime.now().isoformat(),
                "status": "started"
            }
            
            self.learning_history.append(learning_record)
            
            # 这里可以添加实际的学习逻辑
            # 例如：收集相关资料、分析知识空白、制定学习计划等
            
            return True
            
        except Exception as e:
            logger.error(f"启动学习失败: {e}")
            return False
    
    async def analyze_learning_efficiency(self) -> Dict[str, Any]:
        """分析学习效率
        
        Returns:
            学习效率分析结果
        """
        try:
            if len(self.learning_history) < 5:
                return {
                    "needs_improvement": False,
                    "efficiency_score": 0.5,
                    "recommendations": ["需要更多学习数据进行分析"]
                }
            
            # 简单的效率分析
            # 计算最近学习活动的成功率
            recent_learning = self.learning_history[-10:] if len(self.learning_history) >= 10 else self.learning_history
            
            success_count = 0
            for record in recent_learning:
                if record.get("status") == "completed" or record.get("status") == "started":
                    success_count += 1
            
            efficiency_score = success_count / len(recent_learning) if recent_learning else 0.0
            
            needs_improvement = efficiency_score < 0.6
            
            recommendations = []
            if needs_improvement:
                recommendations.append("提高学习成功率")
                recommendations.append("优化学习策略")
            
            return {
                "needs_improvement": needs_improvement,
                "efficiency_score": efficiency_score,
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"分析学习效率失败: {e}")
            return {
                "needs_improvement": True,
                "efficiency_score": 0.0,
                "recommendations": ["分析过程出错"]
            }
    
    async def optimize_learning_strategy(self, recommendations: List[str]):
        """优化学习策略
        
        Args:
            recommendations: 优化建议列表
        """
        try:
            logger.info(f"优化学习策略: {recommendations}")
            
            # 根据建议调整学习策略
            for recommendation in recommendations:
                if "学习率" in recommendation:
                    # 调整学习率
                    self.learning_rate = min(1.0, self.learning_rate + 0.05)
                    logger.info(f"学习率调整为: {self.learning_rate}")
                elif "策略" in recommendation:
                    # 优化学习策略
                    logger.info("优化学习策略逻辑")
            
            # 记录优化操作
            optimization_record = {
                "timestamp": datetime.now().isoformat(),
                "recommendations": recommendations,
                "learning_rate_after": self.learning_rate
            }
            
            self.learning_history.append({
                "timestamp": datetime.now().isoformat(),
                "type": "optimization",
                "optimization": optimization_record
            })
            
            logger.info("学习策略优化完成")
            
        except Exception as e:
            logger.error(f"优化学习策略失败: {e}")
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """获取学习统计信息
        
        Returns:
            学习统计信息
        """
        return {
            "learning_history_count": len(self.learning_history),
            "learning_rate": self.learning_rate,
            "recent_learning_count": min(10, len(self.learning_history)),
            "last_learning_time": self.learning_history[-1].get("timestamp") if self.learning_history else "N/A"
        }
