#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统1模块
负责快速直觉决策
"""

import time
from typing import Dict, List, Optional, Any


class System1:
    """系统1
    
    负责快速直觉决策，基于启发式和经验
    """
    
    def __init__(self):
        """初始化系统1"""
        # 启发式规则
        self.heuristics = {
            "similarity": self._similarity_heuristic,
            "availability": self._availability_heuristic,
            "anchoring": self._anchoring_heuristic
        }
        # 经验记忆
        self.experience_memory = {}
    
    def make_decision(self, situation: Dict[str, Any]) -> Dict[str, Any]:
        """快速决策
        
        Args:
            situation: 当前情况
            
        Returns:
            决策结果
        """
        start_time = time.time()
        
        # 识别情况类型
        situation_type = self._identify_situation_type(situation)
        
        # 应用启发式规则
        decision = self._apply_heuristics(situation, situation_type)
        
        # 记录经验
        self._record_experience(situation, decision)
        
        decision_time = time.time() - start_time
        
        return {
            "decision": decision,
            "confidence": self._calculate_confidence(situation, decision),
            "time_taken": decision_time,
            "system": "System1"
        }
    
    def _identify_situation_type(self, situation: Dict[str, Any]) -> str:
        """识别情况类型
        
        Args:
            situation: 当前情况
            
        Returns:
            情况类型
        """
        # 简单的情况类型识别
        if "emergency" in situation and situation["emergency"]:
            return "emergency"
        elif "routine" in situation and situation["routine"]:
            return "routine"
        elif "novel" in situation and situation["novel"]:
            return "novel"
        else:
            return "normal"
    
    def _apply_heuristics(self, situation: Dict[str, Any], situation_type: str) -> Any:
        """应用启发式规则
        
        Args:
            situation: 当前情况
            situation_type: 情况类型
            
        Returns:
            决策结果
        """
        # 根据情况类型应用不同的启发式规则
        if situation_type == "emergency":
            # 紧急情况：使用可用性启发式
            return self.heuristics["availability"](situation)
        elif situation_type == "routine":
            # 常规情况：使用相似性启发式
            return self.heuristics["similarity"](situation)
        elif situation_type == "novel":
            # 新情况：使用锚定启发式
            return self.heuristics["anchoring"](situation)
        else:
            # 正常情况：综合使用多种启发式
            similarity_decision = self.heuristics["similarity"](situation)
            availability_decision = self.heuristics["availability"](situation)
            
            # 简单的决策融合
            if similarity_decision == availability_decision:
                return similarity_decision
            else:
                return similarity_decision
    
    def _similarity_heuristic(self, situation: Dict[str, Any]) -> Any:
        """相似性启发式
        
        Args:
            situation: 当前情况
            
        Returns:
            决策结果
        """
        # 寻找相似的过去经验
        for past_situation, past_decision in self.experience_memory.items():
            if self._calculate_similarity(situation, past_situation) > 0.7:
                return past_decision
        
        # 如果没有相似经验，返回默认决策
        return "default_decision"
    
    def _availability_heuristic(self, situation: Dict[str, Any]) -> Any:
        """可用性启发式
        
        Args:
            situation: 当前情况
            
        Returns:
            决策结果
        """
        # 基于最近的经验做出决策
        recent_decisions = list(self.experience_memory.values())[-5:]  # 最近5个决策
        if recent_decisions:
            # 返回最常见的决策
            from collections import Counter
            return Counter(recent_decisions).most_common(1)[0][0]
        else:
            return "emergency_decision"
    
    def _anchoring_heuristic(self, situation: Dict[str, Any]) -> Any:
        """锚定启发式
        
        Args:
            situation: 当前情况
            
        Returns:
            决策结果
        """
        # 基于初始信息做出决策
        if "initial_anchor" in situation:
            return situation["initial_anchor"]
        else:
            return "novel_decision"
    
    def _calculate_similarity(self, situation1: Dict[str, Any], situation2: Dict[str, Any]) -> float:
        """计算两个情况的相似度
        
        Args:
            situation1: 第一个情况
            situation2: 第二个情况
            
        Returns:
            相似度（0-1）
        """
        # 简单的相似度计算
        common_keys = set(situation1.keys()) & set(situation2.keys())
        if not common_keys:
            return 0.0
        
        matches = 0
        for key in common_keys:
            if situation1[key] == situation2[key]:
                matches += 1
        
        return matches / len(common_keys)
    
    def _calculate_confidence(self, situation: Dict[str, Any], decision: Any) -> float:
        """计算决策的置信度
        
        Args:
            situation: 当前情况
            decision: 决策结果
            
        Returns:
            置信度（0-1）
        """
        # 基于经验的置信度计算
        similar_experiences = 0
        total_experiences = len(self.experience_memory)
        
        if total_experiences == 0:
            return 0.5
        
        for past_situation, past_decision in self.experience_memory.items():
            if self._calculate_similarity(situation, past_situation) > 0.7 and past_decision == decision:
                similar_experiences += 1
        
        return similar_experiences / total_experiences
    
    def _record_experience(self, situation: Dict[str, Any], decision: Any):
        """记录经验
        
        Args:
            situation: 当前情况
            decision: 决策结果
        """
        # 记录经验，使用情况的字符串表示作为键
        situation_key = str(situation)
        self.experience_memory[situation_key] = decision
        
        # 限制经验记忆的大小
        if len(self.experience_memory) > 1000:
            # 删除最旧的经验
            oldest_key = list(self.experience_memory.keys())[0]
            del self.experience_memory[oldest_key]