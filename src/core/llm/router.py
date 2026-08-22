#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能LLM路由器
支持多种路由策略和负载均衡

路由策略：
- 轮询（Round Robin）
- 随机（Random）
- 最快响应（Least Response Time）
- 成本最优（Cost Optimal）
- 质量优先（Quality First）
- 备用（Failover）

故障转移：
- 自动故障转移到备用模型
- 熔断器模式
- 重试机制
"""

import logging
import random
import time
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from .base_llm import BaseLLM, LLMConfig, LLMResponse, Message, LLMRouter, LLMPool

logger = logging.getLogger(__name__)


class RoutingStrategy(Enum):
    """路由策略"""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_RESPONSE_TIME = "least_response_time"
    COST_OPTIMAL = "cost_optimal"
    QUALITY_FIRST = "quality_first"
    FAILOVER = "failover"


@dataclass
class ModelMetrics:
    """模型性能指标"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    avg_response_time: float = 0.0
    last_request_time: float = 0.0
    last_error: Optional[str] = None
    is_healthy: bool = True
    consecutive_failures: int = 0


@dataclass
class ModelCost:
    """模型成本"""
    input_cost_per_1k: float  # 输入成本（每1K token）
    output_cost_per_1k: float  # 输出成本（每1K token）
    currency: str = "USD"


class IntelligentRouter:
    """智能路由器

    支持多种路由策略和自动故障转移。
    """

    def __init__(self, strategy: RoutingStrategy = RoutingStrategy.ROUND_ROBIN):
        """初始化智能路由器

        Args:
            strategy: 默认路由策略
        """
        self.strategy = strategy
        self.providers: List[BaseLLM] = []
        self.current_index = 0
        self.metrics: Dict[str, ModelMetrics] = defaultdict(ModelMetrics)
        self.costs: Dict[str, ModelCost] = {}

        # 配置参数
        self.circuit_breaker_threshold = 5  # 熔断器阈值
        self.circuit_breaker_timeout = 60  # 熔断器恢复时间（秒）
        self.retry_attempts = 3  # 重试次数
        self.retry_delay = 1.0  # 重试延迟（秒）

        logger.info(f"IntelligentRouter initialized with strategy: {strategy}")

    def add_provider(
        self,
        llm: BaseLLM,
        cost: Optional[ModelCost] = None,
        priority: int = 1
    ):
        """添加LLM提供商

        Args:
            llm: LLM实例
            cost: 模型成本（可选）
            priority: 优先级
        """
        self.providers.append(llm)
        self.metrics[llm.model] = ModelMetrics()

        if cost:
            self.costs[llm.model] = cost

        logger.info(f"Added provider: {llm.provider}/{llm.model}")

    def set_strategy(self, strategy: RoutingStrategy):
        """设置路由策略

        Args:
            strategy: 路由策略
        """
        self.strategy = strategy
        logger.info(f"Routing strategy changed to: {strategy}")

    def select_provider(
        self,
        criteria: Optional[Callable[[BaseLLM], float]] = None
    ) -> Optional[BaseLLM]:
        """选择LLM提供商

        Args:
            criteria: 自定义选择标准

        Returns:
            选中的LLM实例
        """
        healthy = self._get_healthy_providers()

        if not healthy:
            logger.error("No healthy providers available")
            return None

        if criteria:
            # 使用自定义标准
            scored = [(llm, criteria(llm)) for llm in healthy]
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[0][0] if scored else None

        # 使用策略选择
        if self.strategy == RoutingStrategy.ROUND_ROBIN:
            return self._round_robin_select(healthy)
        elif self.strategy == RoutingStrategy.RANDOM:
            return self._random_select(healthy)
        elif self.strategy == RoutingStrategy.LEAST_RESPONSE_TIME:
            return self._least_response_time_select(healthy)
        elif self.strategy == RoutingStrategy.COST_OPTIMAL:
            return self._cost_optimal_select(healthy)
        elif self.strategy == RoutingStrategy.QUALITY_FIRST:
            return self._quality_first_select(healthy)
        elif self.strategy == RoutingStrategy.FAILOVER:
            return self._failover_select(healthy)
        else:
            return healthy[0]

    def _round_robin_select(self, providers: List[BaseLLM]) -> BaseLLM:
        """轮询选择"""
        llm = providers[self.current_index % len(providers)]
        self.current_index += 1
        return llm

    def _random_select(self, providers: List[BaseLLM]) -> BaseLLM:
        """随机选择"""
        return random.choice(providers)

    def _least_response_time_select(self, providers: List[BaseLLM]) -> BaseLLM:
        """选择响应时间最短的"""
        best = None
        best_time = float('inf')

        for llm in providers:
            metrics = self.metrics.get(llm.model)
            if metrics and metrics.avg_response_time < best_time:
                best_time = metrics.avg_response_time
                best = llm

        return best or providers[0]

    def _cost_optimal_select(self, providers: List[BaseLLM]) -> BaseLLM:
        """选择成本最优的"""
        best = None
        best_cost = float('inf')

        for llm in providers:
            cost = self.costs.get(llm.model)
            if cost:
                total = cost.input_cost_per_1k + cost.output_cost_per_1k
                if total < best_cost:
                    best_cost = total
                    best = llm

        return best or providers[0]

    def _quality_first_select(self, providers: List[BaseLLM]) -> BaseLLM:
        """选择质量优先的（假设较新的模型质量更高）"""
        # 按模型名称排序，选择最新的
        model_priority = {
            "claude-3-5": 100,
            "claude-3-opus": 90,
            "claude-3-sonnet": 80,
            "gemini-2.0": 100,
            "gemini-1.5": 80,
            "gemini-1.0": 60,
            "llama": 70,
            "doubao-code": 85,
            "doubao-seed-code": 75
        }

        def quality_score(llm: BaseLLM) -> float:
            for prefix, score in model_priority.items():
                if prefix in llm.model:
                    return score
            return 50

        scored = [(llm, quality_score(llm)) for llm in providers]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0] if scored else providers[0]

    def _failover_select(self, providers: List[BaseLLM]) -> BaseLLM:
        """故障转移选择（选择第一个健康的）"""
        return providers[0]

    def _get_healthy_providers(self) -> List[BaseLLM]:
        """获取所有健康的提供商"""
        healthy = []

        for llm in self.providers:
            metrics = self.metrics.get(llm.model)

            # 检查熔断器状态
            if metrics and not metrics.is_healthy:
                time_since_failure = time.time() - metrics.last_request_time
                if time_since_failure > self.circuit_breaker_timeout:
                    # 尝试恢复
                    metrics.is_healthy = True
                    metrics.consecutive_failures = 0
                    logger.info(f"Circuit breaker reset for {llm.model}")

            if llm.is_available():
                healthy.append(llm)

        return healthy

    def record_success(self, model: str, response_time: float):
        """记录成功请求

        Args:
            model: 模型名称
            response_time: 响应时间
        """
        metrics = self.metrics[model]
        metrics.total_requests += 1
        metrics.successful_requests += 1
        metrics.total_response_time += response_time
        metrics.avg_response_time = (
            metrics.total_response_time / metrics.total_requests
        )
        metrics.last_request_time = time.time()
        metrics.consecutive_failures = 0
        metrics.is_healthy = True
        metrics.last_error = None

    def record_failure(self, model: str, error: str):
        """记录失败请求

        Args:
            model: 模型名称
            error: 错误信息
        """
        metrics = self.metrics[model]
        metrics.total_requests += 1
        metrics.failed_requests += 1
        metrics.last_request_time = time.time()
        metrics.last_error = error
        metrics.consecutive_failures += 1

        # 检查是否需要熔断
        if metrics.consecutive_failures >= self.circuit_breaker_threshold:
            metrics.is_healthy = False
            logger.warning(
                f"Circuit breaker opened for {model} after "
                f"{metrics.consecutive_failures} consecutive failures"
            )

    def execute_with_fallback(
        self,
        messages: List[Message],
        preferred_model: Optional[str] = None,
        **kwargs
    ) -> Tuple[LLMResponse, str]:
        """执行带故障转移的请求

        Args:
            messages: 消息列表
            preferred_model: 首选模型
            **kwargs: 其他参数

        Returns:
            (响应, 使用的模型)
        """
        # 确定尝试顺序
        if preferred_model:
            providers_to_try = []
            for llm in self.providers:
                if llm.model == preferred_model:
                    providers_to_try.insert(0, llm)
                else:
                    providers_to_try.append(llm)
        else:
            providers_to_try = self.providers.copy()
            random.shuffle(providers_to_try)

        last_error = None

        for llm in providers_to_try:
            start_time = time.time()

            try:
                logger.info(f"Trying provider: {llm.provider}/{llm.model}")

                response = llm.chat(messages, **kwargs)

                response_time = time.time() - start_time
                self.record_success(llm.model, response_time)

                logger.info(
                    f"Success with {llm.model}, "
                    f"response_time={response_time:.2f}s"
                )

                return response, llm.model

            except Exception as e:
                error_msg = str(e)
                self.record_failure(llm.model, error_msg)
                last_error = error_msg

                logger.warning(
                    f"Failed with {llm.model}: {error_msg}"
                )

                # 等待后重试
                if len(providers_to_try) > 1:
                    time.sleep(self.retry_delay)

        # 所有提供商都失败
        error_msg = f"All providers failed. Last error: {last_error}"
        logger.error(error_msg)
        raise Exception(error_msg)

    def get_metrics(self) -> Dict[str, Any]:
        """获取所有指标

        Returns:
            指标字典
        """
        result = {}

        for model, metrics in self.metrics.items():
            result[model] = {
                "total_requests": metrics.total_requests,
                "successful_requests": metrics.successful_requests,
                "failed_requests": metrics.failed_requests,
                "success_rate": (
                    metrics.successful_requests / metrics.total_requests
                    if metrics.total_requests > 0 else 0
                ),
                "avg_response_time": metrics.avg_response_time,
                "is_healthy": metrics.is_healthy,
                "consecutive_failures": metrics.consecutive_failures
            }

        return result

    def reset_metrics(self):
        """重置所有指标"""
        self.metrics.clear()
        logger.info("All metrics reset")


class CostAwareRouter(IntelligentRouter):
    """成本感知路由器

    在成本约束下选择最优模型。
    """

    def __init__(
        self,
        max_cost_per_request: float = 0.01,
        strategy: RoutingStrategy = RoutingStrategy.COST_OPTIMAL
    ):
        """初始化成本感知路由器

        Args:
            max_cost_per_request: 单次请求最大成本
            strategy: 路由策略
        """
        super().__init__(strategy)
        self.max_cost_per_request = max_cost_per_request

    def _filter_by_budget(self, providers: List[BaseLLM]) -> List[BaseLLM]:
        """过滤预算内的提供商"""
        filtered = []

        for llm in providers:
            cost = self.costs.get(llm.model)
            if cost:
                # 估算成本（假设平均1000 token输入，500 token输出）
                estimated_cost = (
                    cost.input_cost_per_1k * 1.0 +
                    cost.output_cost_per_1k * 0.5
                )

                if estimated_cost <= self.max_cost_per_request:
                    filtered.append(llm)
            else:
                # 未知成本的模型，默认允许
                filtered.append(llm)

        return filtered if filtered else providers

    def select_provider(self, criteria=None) -> Optional[BaseLLM]:
        """选择提供商（先过滤预算）"""
        healthy = self._get_healthy_providers()
        budget_filtered = self._filter_by_budget(healthy)

        if not budget_filtered:
            logger.warning("No providers within budget")
            return healthy[0] if healthy else None

        return super().select_provider(criteria)
