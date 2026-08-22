#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认知协调器模块
协调系统1（直觉快速）和系统2（分析慢速）的决策过程
支持置信度门控切换、决策融合、延迟分析
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum

from .system1 import System1
from .system2 import System2
from .bayesian_brain import BayesianBrain

logger = logging.getLogger(__name__)


class DecisionMode(Enum):
    """决策模式"""
    SYSTEM1_ONLY = "system1_only"       # 仅 System1（极速）
    SYSTEM1_FAST = "system1_fast"       # System1 优先，低置信度升级
    HYBRID_FUSE = "hybrid_fuse"         # 融合 System1 + System2
    SYSTEM2_DEEP = "system2_deep"       # 强制 System2 深度分析
    PARALLEL = "parallel"              # 并行执行后投票融合


@dataclass
class DecisionResult:
    """决策结果"""
    decision: Any
    confidence: float
    time_taken: float
    mode: DecisionMode
    system1_result: Optional[Dict[str, Any]] = None
    system2_result: Optional[Dict[str, Any]] = None
    degraded: bool = False
    degradation_reason: Optional[str] = None
    fusion_details: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class CognitionCoordinator:
    """认知协调器

    协调系统1（快速直觉）和系统2（分析慢速）的决策过程。
    核心流程：
    1. System1 快速决策
    2. 置信度 >= 阈值 → 直接输出
    3. 置信度 < 阈值 → 升级到 System2
    4. 融合或投票得到最终决策
    """

    def __init__(
        self,
        system1: Optional[System1] = None,
        system2: Optional[System2] = None,
        bayesian_brain: Optional[BayesianBrain] = None,
        confidence_threshold: float = 0.7,
        mode: DecisionMode = DecisionMode.SYSTEM1_FAST,
    ):
        """初始化认知协调器

        Args:
            system1: 系统1实例，默认自动创建
            system2: 系统2实例，默认自动创建（含 BayesianBrain）
            bayesian_brain: 贝叶斯大脑实例
            confidence_threshold: System1→System2 升级阈值（默认 0.7）
            mode: 默认决策模式
        """
        # 自动初始化所有子系统
        self.bayesian_brain = bayesian_brain or BayesianBrain()

        self.system1 = system1 if system1 is not None else System1()

        if system2 is not None:
            self.system2 = system2
        else:
            # 自动创建 System2，绑定 BayesianBrain
            self.system2 = System2(bayesian_brain=self.bayesian_brain)

        self.confidence_threshold = confidence_threshold
        self.mode = mode

        # 决策历史
        self.decision_history: List[DecisionResult] = []
        self.max_history = 100

        # 统计
        self.stats = {
            "system1_only": 0,
            "system1_fast": 0,
            "hybrid_fuse": 0,
            "system2_deep": 0,
            "parallel": 0,
        }

        logger.info(
            f"CognitionCoordinator 初始化: "
            f"System1={self.system1 is not None}, "
            f"System2={self.system2 is not None}, "
            f"BayesianBrain={self.bayesian_brain is not None}, "
            f"模式={mode.value}, 阈值={confidence_threshold}"
        )

    def make_decision(
        self,
        situation: Dict[str, Any],
        mode: Optional[DecisionMode] = None,
    ) -> DecisionResult:
        """做出决策（同步入口）

        Args:
            situation: 当前情况
            mode: 决策模式，不传则使用默认模式

        Returns:
            DecisionResult: 决策结果
        """
        start_time = time.time()
        mode = mode or self.mode

        if mode == DecisionMode.SYSTEM1_ONLY:
            result = self._system1_only(situation)
        elif mode == DecisionMode.SYSTEM1_FAST:
            result = self._system1_fast(situation)
        elif mode == DecisionMode.HYBRID_FUSE:
            result = self._hybrid_fuse(situation)
        elif mode == DecisionMode.SYSTEM2_DEEP:
            result = self._system2_deep(situation)
        elif mode == DecisionMode.PARALLEL:
            result = self._parallel_decision(situation)
        else:
            result = self._system1_fast(situation)

        result.time_taken = time.time() - start_time
        self.stats[mode.value] = self.stats.get(mode.value, 0) + 1

        # 记录历史
        self.decision_history.append(result)
        if len(self.decision_history) > self.max_history:
            self.decision_history = self.decision_history[-self.max_history:]

        return result

    async def make_decision_async(
        self,
        situation: Dict[str, Any],
        mode: Optional[DecisionMode] = None,
    ) -> DecisionResult:
        """异步决策入口"""
        return self.make_decision(situation, mode)

    # ---- 各模式的具体实现 ----

    def _system1_only(self, situation: Dict[str, Any]) -> DecisionResult:
        """仅 System1：极速直觉决策"""
        s1_result = self.system1.make_decision(situation)

        return DecisionResult(
            decision=s1_result.get("decision"),
            confidence=s1_result.get("confidence", 0.5),
            time_taken=0,
            mode=DecisionMode.SYSTEM1_ONLY,
            system1_result=s1_result,
            metadata={"mode": "system1_only"},
        )

    def _system1_fast(self, situation: Dict[str, Any]) -> DecisionResult:
        """System1 优先：置信度门控升级

        如果 System1 置信度 >= 阈值，直接输出；
        否则升级到 System2 进行深度分析，然后融合。
        """
        s1_result = self.system1.make_decision(situation)
        s1_confidence = s1_result.get("confidence", 0.0)

        if s1_confidence >= self.confidence_threshold:
            return DecisionResult(
                decision=s1_result.get("decision"),
                confidence=s1_confidence,
                time_taken=0,
                mode=DecisionMode.SYSTEM1_FAST,
                system1_result=s1_result,
                metadata={"upgraded": False},
            )

        # 升级到 System2
        logger.info(
            f"System1 置信度不足 ({s1_confidence:.2f} < {self.confidence_threshold})，"
            f"升级到 System2"
        )

        if self.system2:
            s2_result = self.system2.make_decision(situation)
            fused = self._fuse_decisions(s1_result, s2_result)
            fused.mode = DecisionMode.SYSTEM1_FAST
            fused.metadata["upgraded"] = True
            return fused

        # 没有 System2，降级用 System1
        return DecisionResult(
            decision=s1_result.get("decision"),
            confidence=s1_confidence * 0.8,
            time_taken=0,
            mode=DecisionMode.SYSTEM1_FAST,
            system1_result=s1_result,
            degraded=True,
            degradation_reason="System2_unavailable",
            metadata={"upgraded": False},
        )

    def _hybrid_fuse(self, situation: Dict[str, Any]) -> DecisionResult:
        """融合模式：同时运行 System1 + System2 后融合"""
        s1_result = self.system1.make_decision(situation)
        s2_result = (
            self.system2.make_decision(situation)
            if self.system2
            else s1_result
        )
        return self._fuse_decisions(s1_result, s2_result)

    def _system2_deep(self, situation: Dict[str, Any]) -> DecisionResult:
        """强制深度分析：仅用 System2"""
        if not self.system2:
            logger.warning("System2 不可用，回退到 System1")
            return self._system1_only(situation)

        s2_result = self.system2.make_decision(situation)

        return DecisionResult(
            decision=s2_result.get("decision"),
            confidence=s2_result.get("confidence", 0.5),
            time_taken=0,
            mode=DecisionMode.SYSTEM2_DEEP,
            system2_result=s2_result,
            metadata={
                "reasoning_chain": s2_result.get("reasoning_chain"),
                "evaluation": s2_result.get("evaluation"),
            },
        )

    def _parallel_decision(self, situation: Dict[str, Any]) -> DecisionResult:
        """并行模式：两系统同时运行后投票融合"""
        s1_result = self.system1.make_decision(situation)
        s2_result = (
            self.system2.make_decision(situation)
            if self.system2
            else s1_result
        )

        # 简单投票融合
        s1_decision = s1_result.get("decision")
        s2_decision = s2_result.get("decision")
        s1_confidence = s1_result.get("confidence", 0.5)
        s2_confidence = s2_result.get("confidence", 0.5)

        if s1_decision == s2_decision:
            return DecisionResult(
                decision=s1_decision,
                confidence=max(s1_confidence, s2_confidence),
                time_taken=0,
                mode=DecisionMode.PARALLEL,
                system1_result=s1_result,
                system2_result=s2_result,
                fusion_details={"method": "unanimous", "agreement": 1.0},
            )

        # 加权投票
        total = s1_confidence + s2_confidence
        if total > 0:
            s1_weight = s1_confidence / total
            s2_weight = s2_confidence / total
        else:
            s1_weight = s2_weight = 0.5

        if s1_weight >= s2_weight:
            final_decision, final_conf = s1_decision, s1_confidence
        else:
            final_decision, final_conf = s2_decision, s2_confidence

        return DecisionResult(
            decision=final_decision,
            confidence=final_conf * max(s1_weight, s2_weight),
            time_taken=0,
            mode=DecisionMode.PARALLEL,
            system1_result=s1_result,
            system2_result=s2_result,
            fusion_details={
                "method": "weighted_vote",
                "s1_weight": s1_weight,
                "s2_weight": s2_weight,
                "agreement": 0.0,
            },
        )

    # ---- 辅助方法 ----

    def _fuse_decisions(
        self,
        system1_decision: Dict[str, Any],
        system2_decision: Dict[str, Any],
    ) -> DecisionResult:
        """融合 System1 和 System2 的决策

        使用加权融合策略，根据置信度权重组合两个系统的结果。
        """
        s1_decision = system1_decision.get("decision")
        s2_decision = system2_decision.get("decision")
        s1_confidence = system1_decision.get("confidence", 0.5)
        s2_confidence = system2_decision.get("confidence", 0.5)

        # 如果一致，取较高置信度
        if s1_decision == s2_decision:
            return DecisionResult(
                decision=s1_decision,
                confidence=max(s1_confidence, s2_confidence),
                time_taken=0,
                mode=DecisionMode.HYBRID_FUSE,
                system1_result=system1_decision,
                system2_result=system2_decision,
                fusion_details={
                    "method": "unanimous",
                    "s1_confidence": s1_confidence,
                    "s2_confidence": s2_confidence,
                },
            )

        # 不一致时加权折中
        total_conf = s1_confidence + s2_confidence
        if total_conf > 0:
            s1_weight = s1_confidence / total_conf
            s2_weight = s2_confidence / total_conf
        else:
            s1_weight = s2_weight = 0.5

        # 选择置信度加权后的决策
        if s1_weight >= s2_weight:
            final_decision = s1_decision
            final_confidence = s1_confidence * 0.9 + s2_confidence * 0.1
        else:
            final_decision = s2_decision
            final_confidence = s2_confidence * 0.9 + s1_confidence * 0.1

        fusion_details = {
            "method": "weighted_fuse",
            "s1_weight": round(s1_weight, 3),
            "s2_weight": round(s2_weight, 3),
            "s1_decision": s1_decision,
            "s2_decision": s2_decision,
            "s1_confidence": round(s1_confidence, 3),
            "s2_confidence": round(s2_confidence, 3),
        }

        return DecisionResult(
            decision=final_decision,
            confidence=round(final_confidence, 3),
            time_taken=0,
            mode=DecisionMode.HYBRID_FUSE,
            system1_result=system1_decision,
            system2_result=system2_decision,
            fusion_details=fusion_details,
        )

    # ---- 查询接口 ----

    def set_confidence_threshold(self, threshold: float):
        """设置置信度阈值

        Args:
            threshold: 新阈值（0-1）
        """
        self.confidence_threshold = max(0.0, min(1.0, threshold))
        logger.info(f"置信度阈值设置为: {self.confidence_threshold}")

    def set_mode(self, mode: DecisionMode):
        """设置决策模式

        Args:
            mode: 决策模式
        """
        self.mode = mode
        logger.info(f"决策模式设置为: {mode.value}")

    def get_history(self, limit: int = 10) -> List[DecisionResult]:
        """获取最近决策历史

        Args:
            limit: 返回条数

        Returns:
            决策历史列表
        """
        return self.decision_history[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """获取协调器统计信息

        Returns:
            统计字典
        """
        total = sum(self.stats.values())
        return {
            "mode": self.mode.value,
            "confidence_threshold": self.confidence_threshold,
            "total_decisions": total,
            "decisions_by_mode": dict(self.stats),
            "mode_distribution": {
                k: round(v / total * 100, 1) if total > 0 else 0
                for k, v in self.stats.items()
            },
            "has_system2": self.system2 is not None,
            "history_size": len(self.decision_history),
        }

    def clear_history(self):
        """清空决策历史"""
        self.decision_history.clear()
        logger.info("决策历史已清空")

    def register_system2_callback(
        self,
        callback: Callable[[Dict[str, Any]], Dict[str, Any]],
    ):
        """注册 System2 回调函数（用于外部推理引擎注入）

        Args:
            callback: 接收 situation，返回决策结果的函数
        """
        original_make = self.system2.make_decision if self.system2 else None

        class WrappedSystem2:
            def make_decision(self, situation):
                return callback(situation)

        self.system2 = WrappedSystem2()
        logger.info("System2 回调已注册")
