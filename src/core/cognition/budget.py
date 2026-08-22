#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推理预算模块 — 控制 LLM 调用量和耗时

提供请求级 BudgetState，每个推理请求独立计数。
不支持反向依赖（由 CoT、ARC、Agent 共同引用）。
"""

import time
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


class ReasoningBudgetExceeded(Exception):
    """推理预算超限"""
    pass


@dataclass(frozen=True)
class ReasoningBudget:
    """推理预算配置（不可变）

    用于创建 BudgetState。
    """
    max_llm_calls: int = 20
    deadline_seconds: float = 30.0

    def __post_init__(self) -> None:
        if self.max_llm_calls < 0:
            raise ValueError("max_llm_calls must be >= 0")
        if self.deadline_seconds <= 0:
            raise ValueError("deadline_seconds must be > 0")


class BudgetState:
    """请求级预算状态

    每个推理请求创建一个，同一请求的 CoT/ToT/Agent 共享同一个实例。
    非线程安全 —— 预期在单事件循环中使用。

    Usage:
        budget = ReasoningBudget(max_llm_calls=5, deadline_seconds=10)
        state = BudgetState(budget)
        # 在 CoT/ARC/Agent 中传递同一个 state
        state.reserve_llm_call()  # 可能抛 ReasoningBudgetExceeded
    """

    __slots__ = ("_max_calls", "_deadline_seconds", "_deadline_at", "_llm_calls")

    def __init__(self, budget: ReasoningBudget):
        self._max_calls: int = budget.max_llm_calls
        self._deadline_seconds: float = budget.deadline_seconds
        self._deadline_at: float = time.monotonic() + budget.deadline_seconds
        self._llm_calls: int = 0

    def reserve_llm_call(self) -> None:
        """预约一次 LLM 调用（计数 + deadline 检查）"""
        now = time.monotonic()
        if now >= self._deadline_at:
            overdue = now - self._deadline_at
            raise ReasoningBudgetExceeded(
                f"推理 deadline 已超出 {overdue:.3f}s，" +
                f"预算为 {self._deadline_seconds:.3f}s"
            )
        if self._llm_calls >= self._max_calls:
            raise ReasoningBudgetExceeded(
                f"LLM 调用次数 {self._llm_calls} 已达上限 {self._max_calls}"
            )
        self._llm_calls += 1

    @property
    def llm_calls(self) -> int:
        return self._llm_calls

    @property
    def remaining_calls(self) -> int:
        return max(0, self._max_calls - self._llm_calls)

    @property
    def remaining_seconds(self) -> float:
        return max(0.0, self._deadline_at - time.monotonic())

    def reset(self) -> None:
        """重置计数（仅用于测试）"""
        self._llm_calls = 0
