#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认知协调器模块
协调系统1和系统2的决策过程
"""

import time
from typing import Dict, List, Optional, Any
from .system1 import System1


class CognitionCoordinator:
    """认知协调器

    协调系统1和系统2的决策过程
    """

    def __init__(self, system1=None, system2=None):
        """初始化认知协调器

        Args:
            system1: 系统1实例
            system2: 系统2实例
        """
        # 系统1
        self.system1 = system1 if system1 else System1()
        # 系统2
        self.system2 = system2
        # 决策历史
        self.decision_history = []
        # 系统选择阈值
        self.confidence_threshold = 0.7

    def make_decision(self, situation: Dict[str, Any]) -> Dict[str, Any]:
        """做出决策

        Args:
            situation: 当前情况

        Returns:
            决策结果
        """
        start_time = time.time()

        # 首先使用系统1做出快速决策
        system1_decision = self.system1.make_decision(situation)

        # 评估系统1的决策置信度
        if system1_decision["confidence"] >= self.confidence_threshold:
            # 如果系统1的置信度足够高，直接使用系统1的决策
            decision = system1_decision
        else:
            # 如果系统1的置信度不够高，使用系统2进行深度分析
            system2_decision = self.system2.make_decision(situation)

            # 融合两个系统的决策
            decision = self._fuse_decisions(system1_decision, system2_decision)

        # 记录决策历史
        self._record_decision(situation, decision)

        total_time = time.time() - start_time
        decision["total_time"] = total_time

        return decision

    def _fuse_decisions(
        self, system1_decision: Dict[str, Any], system2_decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """融合两个系统的决策

        Args:
            system1_decision: 系统1的决策
            system2_decision: 系统2的决策

        Returns:
            融合后的决策
        """
        # 基于置信度加权融合
        system1_weight = system1_decision["confidence"]
        system2_weight = system2_decision["confidence"]
        total_weight = system1_weight + system2_weight

        # 如果系统2的置信度更高，优先使用系统2的决策
        if system2_weight > system1_weight:
            fused_decision = system2_decision.copy()
            fused_decision["system"] = "System1+System2"
        else:
            fused_decision = system1_decision.copy()
            fused_decision["system"] = "System1+System2"

        # 融合置信度
        fused_decision["confidence"] = (
            system1_weight * system1_decision["confidence"]
            + system2_weight * system2_decision["confidence"]
        ) / total_weight

        # 添加系统2的推理链（如果有）
        if "reasoning_chain" in system2_decision:
            fused_decision["reasoning_chain"] = system2_decision["reasoning_chain"]

        return fused_decision

    def _record_decision(self, situation: Dict[str, Any], decision: Dict[str, Any]):
        """记录决策历史

        Args:
            situation: 当前情况
            decision: 决策结果
        """
        self.decision_history.append(
            {"situation": situation, "decision": decision, "timestamp": time.time()}
        )

        # 限制决策历史的大小
        if len(self.decision_history) > 1000:
            self.decision_history = self.decision_history[-1000:]

    def set_confidence_threshold(self, threshold: float):
        """设置系统选择阈值

        Args:
            threshold: 置信度阈值
        """
        self.confidence_threshold = max(0.0, min(1.0, threshold))

    def get_decision_history(self) -> List[Dict[str, Any]]:
        """获取决策历史

        Returns:
            决策历史
        """
        return self.decision_history

    def analyze_decision_history(self) -> Dict[str, Any]:
        """分析决策历史

        Returns:
            分析结果
        """
        if not self.decision_history:
            return {"message": "No decision history"}

        # 统计系统使用情况
        system_usage = {"System1": 0, "System2": 0, "System1+System2": 0}
        confidence_scores = []
        decision_times = []

        for entry in self.decision_history:
            system = entry["decision"].get("system", "Unknown")
            if system in system_usage:
                system_usage[system] += 1
            else:
                system_usage[system] = 1

            confidence = entry["decision"].get("confidence", 0.0)
            confidence_scores.append(confidence)

            time_taken = entry["decision"].get("time_taken", 0.0)
            decision_times.append(time_taken)

        # 计算统计数据
        avg_confidence = (
            sum(confidence_scores) / len(confidence_scores)
            if confidence_scores
            else 0.0
        )
        avg_decision_time = (
            sum(decision_times) / len(decision_times) if decision_times else 0.0
        )

        return {
            "system_usage": system_usage,
            "average_confidence": avg_confidence,
            "average_decision_time": avg_decision_time,
            "total_decisions": len(self.decision_history),
        }
