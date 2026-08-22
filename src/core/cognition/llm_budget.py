#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推理预算控制与 LLM Provider 接口
统一管理 LLM 调用成本、Token 限制、超时和降级策略
"""
import asyncio
import time
import logging
from typing import Dict, Any, Optional, Protocol, runtime_checkable, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class FallbackPolicy(Enum):
    """降级策略"""
    FAIL_CLOSED = "fail_closed"  # 失败就报错
    RETRY_ONCE = "retry_once"    # 重试一次
    RETRY_THEN_TEMPLATE = "retry_then_template"  # 重试后用模板
    TEMPLATE = "template"        # 直接用模板


@dataclass
class ReasoningBudget:
    """推理预算"""
    max_llm_calls: int = 20
    max_input_tokens: int = 50000
    max_output_tokens: int = 10000
    max_cost_usd: float = 1.0
    deadline_seconds: float = 30.0
    
    # 实际使用统计
    llm_calls_used: int = 0
    input_tokens_used: int = 0
    output_tokens_used: int = 0
    cost_used_usd: float = 0.0
    start_time: float = field(default_factory=time.time)
    
    @property
    def remaining_time(self) -> float:
        """剩余时间（秒）"""
        return max(0.0, self.deadline_seconds - (time.time() - self.start_time))
    
    @property
    def is_exhausted(self) -> bool:
        """预算是否耗尽"""
        return (
            self.llm_calls_used >= self.max_llm_calls or
            self.input_tokens_used >= self.max_input_tokens or
            self.output_tokens_used >= self.max_output_tokens or
            self.cost_used_usd >= self.max_cost_usd or
            self.remaining_time <= 0
        )
    
    @property
    def status(self) -> Dict[str, Any]:
        """预算状态"""
        return {
            "llm_calls": {
                "used": self.llm_calls_used,
                "max": self.max_llm_calls,
                "remaining": self.max_llm_calls - self.llm_calls_used
            },
            "input_tokens": {
                "used": self.input_tokens_used,
                "max": self.max_input_tokens,
                "remaining": self.max_input_tokens - self.input_tokens_used
            },
            "output_tokens": {
                "used": self.output_tokens_used,
                "max": self.max_output_tokens,
                "remaining": self.max_output_tokens - self.output_tokens_used
            },
            "cost_usd": {
                "used": round(self.cost_used_usd, 4),
                "max": self.max_cost_usd,
                "remaining": round(self.max_cost_usd - self.cost_used_usd, 4)
            },
            "time": {
                "used": round(time.time() - self.start_time, 2),
                "max": self.deadline_seconds,
                "remaining": round(self.remaining_time, 2)
            },
            "is_exhausted": self.is_exhausted
        }
    
    def record_call(self, input_tokens: int = 0, output_tokens: int = 0, cost_usd: float = 0.0):
        """记录一次 LLM 调用"""
        self.llm_calls_used += 1
        self.input_tokens_used += input_tokens
        self.output_tokens_used += output_tokens
        self.cost_used_usd += cost_usd


@dataclass
class LLMResult:
    """LLM 调用结果，包含降级标记"""
    content: str
    mode_requested: str = "llm"
    mode_used: str = "llm"
    degraded: bool = False
    degradation_reason: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    attempts: int = 1
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    error: Optional[str] = None


@runtime_checkable
class AsyncLLMProvider(Protocol):
    """异步 LLM Provider 协议"""
    async def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> LLMResult:
        """生成文本"""
        ...


@runtime_checkable
class SyncLLMProvider(Protocol):
    """同步 LLM Provider 协议"""
    def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> LLMResult:
        """生成文本"""
        ...


class BudgetExhaustedError(Exception):
    """预算耗尽异常"""
    pass


class LLMInvoker:
    """LLM 调用器，统一处理同步/异步、超时、降级和预算"""
    
    def __init__(
        self,
        fallback_policy: FallbackPolicy = FallbackPolicy.RETRY_THEN_TEMPLATE,
        default_timeout: float = 10.0,
    ):
        self.fallback_policy = fallback_policy
        self.default_timeout = default_timeout
        self.providers: Dict[str, Any] = {}
        self.default_provider: Optional[str] = None
    
    def register_provider(self, name: str, provider: Any, is_default: bool = False):
        """注册 LLM Provider"""
        self.providers[name] = provider
        if is_default or not self.default_provider:
            self.default_provider = name
        logger.info(f"已注册 LLM Provider: {name}")
    
    async def invoke(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        provider: Optional[str] = None,
        timeout: Optional[float] = None,
        budget: Optional[ReasoningBudget] = None,
        template_fallback: Optional[Callable[[str], str]] = None,
    ) -> LLMResult:
        """
        调用 LLM，统一处理同步/异步、超时、降级和预算
        
        Args:
            prompt: 提示词
            temperature: 温度
            max_tokens: 最大 Token 数
            provider: 指定 Provider，None 则用默认
            timeout: 超时时间，None 则用默认
            budget: 预算控制，None 则不限制
            template_fallback: 模板降级函数，LLM 失败时调用
        
        Returns:
            LLMResult，包含降级标记
        """
        start_time = time.time()
        timeout = timeout or self.default_timeout
        provider_name = provider or self.default_provider
        
        # 预算检查
        if budget and budget.is_exhausted:
            logger.warning(f"预算耗尽，请求模板降级")
            return self._template_fallback_result(
                prompt, template_fallback, "budget_exhausted", start_time
            )
        
        llm_provider = self.providers.get(provider_name) if provider_name else None
        
        if not llm_provider:
            # 没有 Provider，直接降级
            logger.warning(f"无可用 LLM Provider，请求模板降级")
            return self._template_fallback_result(
                prompt, template_fallback, "no_provider", start_time
            )
        
        attempts = 0
        max_attempts = 2 if self.fallback_policy in [FallbackPolicy.RETRY_ONCE, FallbackPolicy.RETRY_THEN_TEMPLATE] else 1
        
        while attempts < max_attempts:
            attempts += 1
            try:
                # 统一处理同步和异步 Provider
                generate_func = getattr(llm_provider, "generate", None)
                if not generate_func:
                    raise ValueError(f"Provider {provider_name} 没有 generate 方法")
                
                # 异步调用或线程池包装
                if asyncio.iscoroutinefunction(generate_func):
                    result = await asyncio.wait_for(
                        generate_func(prompt, temperature=temperature, max_tokens=max_tokens),
                        timeout=timeout
                    )
                else:
                    # 同步函数放入线程池执行，避免阻塞事件循环
                    result = await asyncio.wait_for(
                        asyncio.to_thread(
                            generate_func, prompt, temperature=temperature, max_tokens=max_tokens
                        ),
                        timeout=timeout
                    )
                
                # 确保结果是 LLMResult 类型
                if not isinstance(result, LLMResult):
                    result = LLMResult(content=str(result))
                
                result.attempts = attempts
                result.latency_ms = (time.time() - start_time) * 1000
                result.provider = provider_name
                
                # 记录预算
                if budget:
                    budget.record_call(
                        input_tokens=result.input_tokens,
                        output_tokens=result.output_tokens,
                        cost_usd=result.cost_usd
                    )
                
                return result
                
            except asyncio.TimeoutError:
                logger.warning(f"LLM 调用超时 (尝试 {attempts}/{max_attempts})")
                if attempts >= max_attempts:
                    return self._template_fallback_result(
                        prompt, template_fallback, "timeout", start_time
                    )
            except Exception as e:
                logger.warning(f"LLM 调用失败 (尝试 {attempts}/{max_attempts}): {e}")
                if attempts >= max_attempts:
                    return self._template_fallback_result(
                        prompt, template_fallback, f"error: {str(e)}", start_time
                    )
        
        # 理论上不会到这里
        return self._template_fallback_result(
            prompt, template_fallback, "max_attempts_reached", start_time
        )
    
    def _template_fallback_result(
        self,
        prompt: str,
        template_func: Optional[Callable[[str], str]],
        reason: str,
        start_time: float,
    ) -> LLMResult:
        """模板降级结果"""
        if template_func and self.fallback_policy not in [FallbackPolicy.FAIL_CLOSED]:
            content = template_func(prompt)
            return LLMResult(
                content=content,
                mode_used="template",
                degraded=True,
                degradation_reason=reason,
                latency_ms=(time.time() - start_time) * 1000,
            )
        else:
            return LLMResult(
                content="",
                mode_used="failed",
                degraded=True,
                degradation_reason=f"fail_closed: {reason}",
                error=f"LLM 调用失败且禁用降级: {reason}",
                latency_ms=(time.time() - start_time) * 1000,
            )


# 全局单例
_global_invoker: Optional[LLMInvoker] = None


def get_llm_invoker() -> LLMInvoker:
    """获取全局 LLM 调用器"""
    global _global_invoker
    if _global_invoker is None:
        _global_invoker = LLMInvoker()
    return _global_invoker
