#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 速率限制模块
实现精细化的请求速率控制，保护系统稳定性
集成 OpenTelemetry 追踪限流触发链路
"""

import logging
import time
from typing import Dict, Optional, Any, Tuple
from collections import deque
from threading import Lock

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 尝试导入 OpenTelemetry
try:
    from opentelemetry import trace
    from opentelemetry.trace import SpanKind, StatusCode
    HAS_OPENTELEMETRY = True
    logger.info("OpenTelemetry 已加载，将启用限流追踪")
except ImportError:
    HAS_OPENTELEMETRY = False
    logger.warning("OpenTelemetry 未安装，限流追踪将被禁用")


class RateLimitExceededError(Exception):
    """速率限制超出异常"""
    
    def __init__(self, message: str, retry_after: float):
        super().__init__(message)
        self.retry_after = retry_after


class TokenBucket:
    """令牌桶算法实现"""
    
    def __init__(self, capacity: int, rate: float):
        """
        初始化令牌桶
        
        Args:
            capacity: 桶的容量（最大令牌数）
            rate: 令牌生成速率（每秒生成的令牌数）
        """
        self.capacity = capacity
        self.rate = rate
        self.tokens = capacity
        self.last_refill_time = time.time()
        self.lock = Lock()
    
    def _refill(self):
        """补充令牌"""
        now = time.time()
        elapsed = now - self.last_refill_time
        new_tokens = elapsed * self.rate
        self.tokens = min(self.tokens + new_tokens, self.capacity)
        self.last_refill_time = now
    
    def try_acquire(self, tokens: int = 1) -> bool:
        """尝试获取令牌"""
        with self.lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def get_tokens(self) -> float:
        """获取当前令牌数"""
        with self.lock:
            self._refill()
            return self.tokens
    
    def get_retry_after(self) -> float:
        """获取需要等待的时间（秒）"""
        with self.lock:
            self._refill()
            if self.tokens >= 1:
                return 0.0
            return (1 - self.tokens) / self.rate


class SlidingWindowCounter:
    """滑动窗口计数器"""
    
    def __init__(self, window_seconds: int, max_requests: int):
        """
        初始化滑动窗口计数器
        
        Args:
            window_seconds: 窗口大小（秒）
            max_requests: 窗口内最大请求数
        """
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self.timestamps = deque()
        self.lock = Lock()
    
    def try_acquire(self) -> Tuple[bool, float]:
        """尝试获取请求权限"""
        with self.lock:
            now = time.time()
            
            # 移除窗口外的记录
            cutoff = now - self.window_seconds
            while self.timestamps and self.timestamps[0] < cutoff:
                self.timestamps.popleft()
            
            if len(self.timestamps) < self.max_requests:
                self.timestamps.append(now)
                return True, 0.0
            
            # 计算需要等待的时间
            oldest_time = self.timestamps[0] if self.timestamps else now
            retry_after = max(0.0, oldest_time + self.window_seconds - now)
            return False, retry_after
    
    def get_current_count(self) -> int:
        """获取当前窗口内的请求数"""
        with self.lock:
            now = time.time()
            cutoff = now - self.window_seconds
            while self.timestamps and self.timestamps[0] < cutoff:
                self.timestamps.popleft()
            return len(self.timestamps)


class RateLimiter:
    """速率限制器，支持多种限流策略"""
    
    def __init__(self):
        self.buckets: Dict[str, TokenBucket] = {}
        self.windows: Dict[str, SlidingWindowCounter] = {}
        self.lock = Lock()
        self._tracer = trace.get_tracer("rate_limiter") if HAS_OPENTELEMETRY else None
    
    def _create_span(self, name: str, key: str, attributes: Optional[Dict[str, Any]] = None):
        """创建追踪 span"""
        if not HAS_OPENTELEMETRY or not self._tracer:
            return None
        
        span = self._tracer.start_span(name, kind=SpanKind.INTERNAL)
        span.set_attribute("rate_limit.key", key)
        if attributes:
            for attr_key, attr_value in attributes.items():
                span.set_attribute(f"rate_limit.{attr_key}", attr_value)
        return span
    
    def configure_token_bucket(self, key: str, capacity: int, rate: float):
        """配置令牌桶限流"""
        with self.lock:
            self.buckets[key] = TokenBucket(capacity, rate)
            logger.info(f"配置令牌桶: {key}, 容量: {capacity}, 速率: {rate}/s")
    
    def configure_sliding_window(self, key: str, window_seconds: int, max_requests: int):
        """配置滑动窗口限流"""
        with self.lock:
            self.windows[key] = SlidingWindowCounter(window_seconds, max_requests)
            logger.info(f"配置滑动窗口: {key}, 窗口: {window_seconds}s, 最大请求: {max_requests}")
    
    def try_acquire_token_bucket(self, key: str) -> Tuple[bool, float]:
        """尝试通过令牌桶获取权限"""
        bucket = self.buckets.get(key)
        if not bucket:
            return True, 0.0
        
        if bucket.try_acquire():
            return True, 0.0
        
        retry_after = bucket.get_retry_after()
        # 记录限流触发的追踪
        span = self._create_span(
            "rate_limit.token_bucket.blocked",
            key,
            {
                "type": "token_bucket",
                "capacity": bucket.capacity,
                "rate": bucket.rate,
                "tokens": bucket.get_tokens(),
                "retry_after": retry_after,
                "blocked": True
            }
        )
        if span:
            span.set_status(StatusCode.ERROR, "Rate limit exceeded")
            span.end()
        
        logger.warning(f"令牌桶限流触发: key={key}, 需要等待={retry_after:.2f}s")
        return False, retry_after
    
    def try_acquire_sliding_window(self, key: str) -> Tuple[bool, float]:
        """尝试通过滑动窗口获取权限"""
        window = self.windows.get(key)
        if not window:
            return True, 0.0
        
        success, retry_after = window.try_acquire()
        
        if not success:
            # 记录限流触发的追踪
            span = self._create_span(
                "rate_limit.sliding_window.blocked",
                key,
                {
                    "type": "sliding_window",
                    "window_seconds": window.window_seconds,
                    "max_requests": window.max_requests,
                    "current_count": window.get_current_count(),
                    "retry_after": retry_after,
                    "blocked": True
                }
            )
            if span:
                span.set_status(StatusCode.ERROR, "Rate limit exceeded")
                span.end()
            
            logger.warning(f"滑动窗口限流触发: key={key}, 需要等待={retry_after:.2f}s")
        
        return success, retry_after
    
    def check_rate_limit(self, key: str) -> Tuple[bool, float]:
        """检查速率限制（同时检查令牌桶和滑动窗口）"""
        span = self._create_span("rate_limit.check", key)
        
        # 先检查令牌桶
        bucket_ok, bucket_retry = self.try_acquire_token_bucket(key)
        if not bucket_ok:
            if span:
                span.set_attribute("rate_limit.blocked_by", "token_bucket")
                span.set_attribute("rate_limit.retry_after", bucket_retry)
                span.set_status(StatusCode.ERROR, "Rate limit exceeded by token bucket")
                span.end()
            logger.warning(f"速率限制触发 [令牌桶]: key={key}, retry_after={bucket_retry:.2f}s")
            return False, bucket_retry
        
        # 再检查滑动窗口
        window_ok, window_retry = self.try_acquire_sliding_window(key)
        if not window_ok:
            if span:
                span.set_attribute("rate_limit.blocked_by", "sliding_window")
                span.set_attribute("rate_limit.retry_after", window_retry)
                span.set_status(StatusCode.ERROR, "Rate limit exceeded by sliding window")
                span.end()
            logger.warning(f"速率限制触发 [滑动窗口]: key={key}, retry_after={window_retry:.2f}s")
            return False, window_retry
        
        # 检查通过
        if span:
            span.set_attribute("rate_limit.blocked", False)
            span.set_status(StatusCode.OK)
            span.end()
        
        logger.debug(f"速率限制检查通过: key={key}")
        return True, 0.0
    
    def get_stats(self, key: str) -> Dict[str, Any]:
        """获取限流统计信息"""
        stats = {}
        
        if key in self.buckets:
            bucket = self.buckets[key]
            stats["token_bucket"] = {
                "tokens": bucket.get_tokens(),
                "capacity": bucket.capacity,
                "rate": bucket.rate
            }
        
        if key in self.windows:
            window = self.windows[key]
            stats["sliding_window"] = {
                "current_count": window.get_current_count(),
                "max_requests": window.max_requests,
                "window_seconds": window.window_seconds
            }
        
        return stats


# 全局速率限制器实例
rate_limiter = RateLimiter()


def rate_limit(key: str):
    """装饰器：为方法添加速率限制"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            ok, retry_after = rate_limiter.check_rate_limit(key)
            if not ok:
                raise RateLimitExceededError(
                    f"速率限制超出，请在 {retry_after:.2f} 秒后重试",
                    retry_after
                )
            return await func(*args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            ok, retry_after = rate_limiter.check_rate_limit(key)
            if not ok:
                raise RateLimitExceededError(
                    f"速率限制超出，请在 {retry_after:.2f} 秒后重试",
                    retry_after
                )
            return func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


def setup_default_rate_limits():
    """设置默认的速率限制规则"""
    # 记忆系统写入限制
    rate_limiter.configure_token_bucket("memory_write", capacity=100, rate=50)
    rate_limiter.configure_sliding_window("memory_write", window_seconds=60, max_requests=3000)
    
    # 记忆系统读取限制
    rate_limiter.configure_token_bucket("memory_read", capacity=200, rate=100)
    rate_limiter.configure_sliding_window("memory_read", window_seconds=60, max_requests=6000)
    
    # 向量索引查询限制
    rate_limiter.configure_token_bucket("vector_query", capacity=50, rate=20)
    rate_limiter.configure_sliding_window("vector_query", window_seconds=60, max_requests=1200)
    
    # 知识图谱查询限制
    rate_limiter.configure_token_bucket("graph_query", capacity=30, rate=15)
    rate_limiter.configure_sliding_window("graph_query", window_seconds=60, max_requests=900)
    
    logger.info("默认速率限制规则已配置")


async def main():
    """示例用法"""
    setup_default_rate_limits()
    
    @rate_limit("test_endpoint")
    async def test_endpoint():
        return "success"
    
    # 测试速率限制
    for i in range(20):
        try:
            result = await test_endpoint()
            print(f"请求 {i+1}: {result}")
        except RateLimitExceededError as e:
            print(f"请求 {i+1}: 速率限制超出，需要等待 {e.retry_after:.2f} 秒")
            break


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
