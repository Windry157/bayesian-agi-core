#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
置信度评分器模块
实现不确定性量化与置信度评分
支持决策置信度和文本生成置信度评估
"""

import logging
import math
import asyncio
import statistics
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """置信度评分器
    
    实现多种置信度评分方法：
    1. 决策置信度（基于知识覆盖率、记忆匹配度等）
    2. 文本生成置信度（基于熵/困惑度、一致性等）
    """
    
    def __init__(self):
        """初始化置信度评分器"""
        self.scoring_history = []
        self.confidence_thresholds = {
            "high": 0.8,      # 高置信度：直接回答
            "medium": 0.6,    # 中等置信度：提供警告
            "low": 0.4,       # 低置信度：请求澄清
            "very_low": 0.2   # 极低置信度：拒绝回答
        }
        
        logger.info("置信度评分器初始化完成")
    
    async def score_decision_confidence(
        self, 
        decision_context: Dict[str, Any],
        relevant_memories: List[Dict[str, Any]],
        knowledge_coverage: float
    ) -> Dict[str, Any]:
        """评分决策置信度
        
        Args:
            decision_context: 决策上下文
            relevant_memories: 相关记忆列表
            knowledge_coverage: 知识覆盖率（0-1）
            
        Returns:
            置信度评分结果
        """
        try:
            # 因子1：记忆匹配度
            memory_match_score = self._calculate_memory_match_score(relevant_memories)
            
            # 因子2：上下文一致性
            context_consistency_score = self._calculate_context_consistency(decision_context)
            
            # 因子3：知识覆盖率
            knowledge_coverage_score = knowledge_coverage
            
            # 因子4：决策历史相似度（如果有历史）
            historical_similarity_score = self._calculate_historical_similarity(decision_context)
            
            # 综合置信度（加权平均）
            confidence = (
                memory_match_score * 0.3 +
                context_consistency_score * 0.25 +
                knowledge_coverage_score * 0.3 +
                historical_similarity_score * 0.15
            )
            
            # 置信度分类
            confidence_level = self._classify_confidence(confidence)
            
            # 不确定性分析
            uncertainty_analysis = self._analyze_uncertainty(
                memory_match_score,
                context_consistency_score,
                knowledge_coverage_score,
                historical_similarity_score
            )
            
            result = {
                "confidence_score": confidence,
                "confidence_level": confidence_level,
                "uncertainty_analysis": uncertainty_analysis,
                "factor_scores": {
                    "memory_match": memory_match_score,
                    "context_consistency": context_consistency_score,
                    "knowledge_coverage": knowledge_coverage_score,
                    "historical_similarity": historical_similarity_score
                },
                "timestamp": datetime.now().isoformat()
            }
            
            # 记录评分历史
            self._record_scoring(result)
            
            logger.info(f"决策置信度评分完成: {confidence:.3f} ({confidence_level})")
            return result
            
        except Exception as e:
            logger.error(f"决策置信度评分失败: {e}")
            return {
                "confidence_score": 0.5,
                "confidence_level": "unknown",
                "uncertainty_analysis": {"error": str(e)},
                "factor_scores": {},
                "timestamp": datetime.now().isoformat()
            }
    
    async def score_text_generation_confidence(
        self,
        prompt: str,
        generated_text: str,
        model_output: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """评分文本生成置信度
        
        Args:
            prompt: 输入提示
            generated_text: 生成的文本
            model_output: 模型原始输出（包含概率信息）
            
        Returns:
            置信度评分结果
        """
        try:
            # 因子1：文本一致性（自洽性检查）
            consistency_score = self._calculate_text_consistency(generated_text)
            
            # 因子2：提示相关性
            relevance_score = self._calculate_prompt_relevance(prompt, generated_text)
            
            # 因子3：语法正确性（简单检查）
            grammar_score = self._calculate_grammar_score(generated_text)
            
            # 因子4：模型置信度（如果有概率信息）
            model_confidence_score = self._extract_model_confidence(model_output)
            
            # 综合置信度
            confidence = (
                consistency_score * 0.3 +
                relevance_score * 0.3 +
                grammar_score * 0.2 +
                model_confidence_score * 0.2
            )
            
            # 置信度分类
            confidence_level = self._classify_confidence(confidence)
            
            result = {
                "confidence_score": confidence,
                "confidence_level": confidence_level,
                "factor_scores": {
                    "consistency": consistency_score,
                    "relevance": relevance_score,
                    "grammar": grammar_score,
                    "model_confidence": model_confidence_score
                },
                "timestamp": datetime.now().isoformat()
            }
            
            # 记录评分历史
            self._record_scoring(result)
            
            logger.info(f"文本生成置信度评分完成: {confidence:.3f} ({confidence_level})")
            return result
            
        except Exception as e:
            logger.error(f"文本生成置信度评分失败: {e}")
            return {
                "confidence_score": 0.5,
                "confidence_level": "unknown",
                "factor_scores": {},
                "timestamp": datetime.now().isoformat()
            }
    
    def _calculate_memory_match_score(self, memories: List[Dict[str, Any]]) -> float:
        """计算记忆匹配度
        
        Args:
            memories: 相关记忆列表
            
        Returns:
            记忆匹配度分数（0-1）
        """
        if not memories:
            return 0.2  # 没有记忆，低匹配度
        
        # 基于记忆数量和相似度计算
        memory_count = len(memories)
        
        # 提取相似度分数（如果存在）
        similarity_scores = []
        for memory in memories:
            if "similarity" in memory:
                similarity_scores.append(memory["similarity"])
            elif "score" in memory:
                similarity_scores.append(memory["score"])
        
        if similarity_scores:
            avg_similarity = statistics.mean(similarity_scores)
            # 结合记忆数量和相似度
            match_score = min(0.95, avg_similarity * (0.5 + 0.5 * (min(memory_count, 5) / 5)))
        else:
            # 没有相似度信息，基于数量估计
            match_score = min(0.8, 0.2 + 0.6 * (min(memory_count, 5) / 5))
        
        return match_score
    
    def _calculate_context_consistency(self, context: Dict[str, Any]) -> float:
        """计算上下文一致性
        
        Args:
            context: 决策上下文
            
        Returns:
            上下文一致性分数（0-1）
        """
        # 简化实现：检查关键字段是否存在
        required_fields = ["input", "context", "thought_chain"]
        present_fields = [field for field in required_fields if field in context]
        
        if len(present_fields) == len(required_fields):
            # 所有关键字段都存在
            base_score = 0.7
            
            # 检查思维链长度
            thought_chain = context.get("thought_chain", [])
            if len(thought_chain) >= 3:
                base_score += 0.2
            
            # 检查上下文信息
            relevant_history = context.get("context", {}).get("relevant_history", [])
            if relevant_history:
                base_score += 0.1
            
            return min(0.95, base_score)
        else:
            # 缺失关键字段
            missing_count = len(required_fields) - len(present_fields)
            return max(0.1, 0.5 - missing_count * 0.2)
    
    def _calculate_historical_similarity(self, context: Dict[str, Any]) -> float:
        """计算历史相似度
        
        Args:
            context: 决策上下文
            
        Returns:
            历史相似度分数（0-1）
        """
        # 简化实现：基于输入文本长度和类型估计
        input_text = context.get("input", "")
        if not input_text:
            return 0.5
        
        # 基于输入长度和复杂度估计
        text_length = len(input_text)
        
        if text_length < 10:
            # 简短输入，历史相似度较低
            return 0.3
        elif text_length < 50:
            # 中等长度
            return 0.6
        else:
            # 复杂输入，需要更多历史参考
            return 0.4
    
    def _calculate_text_consistency(self, text: str) -> float:
        """计算文本一致性
        
        Args:
            text: 待检查文本
            
        Returns:
            一致性分数（0-1）
        """
        if not text:
            return 0.0
        
        # 简单的一致性检查：重复词比例
        words = text.lower().split()
        if len(words) < 3:
            return 0.8  # 太短，难以评估
        
        word_count = {}
        for word in words:
            if len(word) > 3:  # 忽略短词
                word_count[word] = word_count.get(word, 0) + 1
        
        # 计算重复率
        total_words = len([w for w in words if len(w) > 3])
        if total_words == 0:
            return 0.7
        
        repeated_words = sum(1 for count in word_count.values() if count > 1)
        repetition_ratio = repeated_words / total_words
        
        # 低重复率表示高一致性
        consistency = 1.0 - min(1.0, repetition_ratio * 2)
        
        return max(0.1, consistency)
    
    def _calculate_prompt_relevance(self, prompt: str, generated_text: str) -> float:
        """计算提示相关性
        
        Args:
            prompt: 输入提示
            generated_text: 生成文本
            
        Returns:
            相关性分数（0-1）
        """
        if not prompt or not generated_text:
            return 0.0
        
        # 简单关键词匹配
        prompt_words = set(prompt.lower().split())
        generated_words = set(generated_text.lower().split())
        
        if not prompt_words:
            return 0.5
        
        # 计算重叠比例
        overlap = len(prompt_words.intersection(generated_words))
        relevance = overlap / len(prompt_words)
        
        return min(1.0, relevance * 1.5)  # 稍微放大
    
    def _calculate_grammar_score(self, text: str) -> float:
        """计算语法正确性分数
        
        Args:
            text: 待检查文本
            
        Returns:
            语法分数（0-1）
        """
        if not text:
            return 0.0
        
        # 简单启发式：句子结尾、标点符号
        sentences = text.split('.')
        if len(sentences) < 2:
            return 0.7  # 单句，难以评估
        
        # 检查句子长度差异（太相似的句子可能有问题）
        sentence_lengths = [len(s.strip()) for s in sentences if s.strip()]
        if len(sentence_lengths) < 2:
            return 0.7
        
        # 计算变异系数
        mean_length = statistics.mean(sentence_lengths)
        if mean_length == 0:
            return 0.5
        
        stdev_length = statistics.stdev(sentence_lengths) if len(sentence_lengths) > 1 else 0
        cv = stdev_length / mean_length
        
        # 中等变异系数表示良好的句子结构
        ideal_cv = 0.5
        grammar_score = 1.0 - min(1.0, abs(cv - ideal_cv) * 2)
        
        return max(0.2, grammar_score)
    
    def _extract_model_confidence(self, model_output: Optional[Dict[str, Any]]) -> float:
        """从模型输出提取置信度
        
        Args:
            model_output: 模型原始输出
            
        Returns:
            模型置信度分数（0-1）
        """
        if not model_output:
            return 0.5  # 默认值
        
        # 检查常见置信度字段
        confidence_fields = ["confidence", "score", "probability", "prob"]
        
        for field in confidence_fields:
            if field in model_output:
                value = model_output[field]
                if isinstance(value, (int, float)):
                    return max(0.0, min(1.0, float(value)))
        
        # 如果没有置信度字段，检查logprobs或token概率
        if "logprobs" in model_output:
            logprobs = model_output["logprobs"]
            if logprobs:
                # 计算平均对数概率
                avg_logprob = statistics.mean(logprobs)
                # 转换为置信度（粗略估计）
                confidence = 1.0 / (1.0 + math.exp(-avg_logprob))
                return confidence
        
        return 0.5
    
    def _analyze_uncertainty(
        self,
        memory_match: float,
        context_consistency: float,
        knowledge_coverage: float,
        historical_similarity: float
    ) -> Dict[str, Any]:
        """分析不确定性来源
        
        Args:
            memory_match: 记忆匹配度
            context_consistency: 上下文一致性
            knowledge_coverage: 知识覆盖率
            historical_similarity: 历史相似度
            
        Returns:
            不确定性分析结果
        """
        uncertainty_sources = []
        
        if memory_match < 0.3:
            uncertainty_sources.append({
                "source": "memory_match",
                "score": memory_match,
                "description": "缺乏相关记忆支持",
                "recommendation": "需要更多领域知识或示例"
            })
        
        if context_consistency < 0.4:
            uncertainty_sources.append({
                "source": "context_consistency",
                "score": context_consistency,
                "description": "上下文信息不完整或不一致",
                "recommendation": "需要澄清问题背景或提供更多上下文"
            })
        
        if knowledge_coverage < 0.3:
            uncertainty_sources.append({
                "source": "knowledge_coverage",
                "score": knowledge_coverage,
                "description": "知识覆盖不足",
                "recommendation": "需要扩展相关知识库"
            })
        
        if historical_similarity < 0.3:
            uncertainty_sources.append({
                "source": "historical_similarity",
                "score": historical_similarity,
                "description": "缺乏类似历史案例",
                "recommendation": "需要更多类似问题的经验"
            })
        
        # 计算总体不确定性
        scores = [memory_match, context_consistency, knowledge_coverage, historical_similarity]
        avg_score = statistics.mean(scores) if scores else 0.5
        overall_uncertainty = 1.0 - avg_score
        
        return {
            "overall_uncertainty": overall_uncertainty,
            "uncertainty_sources": uncertainty_sources,
            "primary_source": uncertainty_sources[0]["source"] if uncertainty_sources else None
        }
    
    def _classify_confidence(self, confidence_score: float) -> str:
        """分类置信度
        
        Args:
            confidence_score: 置信度分数
            
        Returns:
            置信度级别
        """
        if confidence_score >= self.confidence_thresholds["high"]:
            return "high"
        elif confidence_score >= self.confidence_thresholds["medium"]:
            return "medium"
        elif confidence_score >= self.confidence_thresholds["low"]:
            return "low"
        else:
            return "very_low"
    
    def _record_scoring(self, scoring_result: Dict[str, Any]):
        """记录评分结果
        
        Args:
            scoring_result: 评分结果
        """
        self.scoring_history.append(scoring_result)
        
        # 限制历史记录长度
        if len(self.scoring_history) > 1000:
            self.scoring_history = self.scoring_history[-1000:]
    
    def get_scoring_history(self) -> List[Dict[str, Any]]:
        """获取评分历史
        
        Returns:
            评分历史列表
        """
        return self.scoring_history
    
    def set_confidence_threshold(self, level: str, threshold: float):
        """设置置信度阈值
        
        Args:
            level: 置信度级别（high/medium/low/very_low）
            threshold: 阈值（0-1）
        """
        if level in self.confidence_thresholds:
            self.confidence_thresholds[level] = max(0.0, min(1.0, threshold))
            logger.info(f"设置置信度阈值 {level}: {threshold}")
    
    def get_confidence_thresholds(self) -> Dict[str, float]:
        """获取置信度阈值
        
        Returns:
            置信度阈值字典
        """
        return self.confidence_thresholds.copy()


# 全局置信度评分器实例
confidence_scorer = ConfidenceScorer()