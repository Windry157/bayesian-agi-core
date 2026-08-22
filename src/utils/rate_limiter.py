#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
限流器实现
- 滑动窗口算法
- 令牌桶算法
- 固定窗口算法
"""

import time
import asyncio
from collections import defaultdict, deque
from typing import Dict, Deque, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from src.utils.structured_logging import get_logger

logger = get_logger("rate_limiter")


@dataclass
class RateLimitConfig:
    """限流配置"""
    requests: int
    period_seconds: float
    burst_size: Optional[int] = None  # 突发大小


class SlidingWindowRateLimiter:
    """滑动窗口限流器"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.requests: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()
        self._last_cleanup_time = 0.0
        self._cleanup_interval = 30.0  # 每30秒至少清理一次
    
    def _cleanup_old_entries(self):
        """清理过期的请求记录，防止内存泄漏"""
        now = time.time()
        window_start = now - self.config.period_seconds
        
        keys_to_remove = []
        for key, queue in self.requests.items():
            # 移除该 key 的过期请求
            while queue and queue[0] < window_start:
                queue.popleft()
            
            # 如果队列已空，标记该 key 为待删除
            if not queue:
                keys_to_remove.append(key)
        
        # 删除空队列的 key
        for key in keys_to_remove:
            del self.requests[key]
    
    async def acquire(self, key: str) -> bool:
        """
        获取令牌
        
        Args:
            key: 限流键（如用户ID、IP等）
        
        Returns:
            是否允许通过
        """
        now = time.time()
        window_start = now - self.config.period_seconds
        
        async with self._lock:
            # 移除当前 key 过期的请求
            queue = self.requests[key]
            while queue and queue[0] < window_start:
                queue.popleft()
            
            # 检查是否超过限制
            if len(queue) >= self.config.requests:
                logger.warning(
                    f"Rate limit exceeded for key: {key} (current: {len(queue)}, limit: {self.config.requests})"
                )
                return False
            
            queue.append(now)
            
            # 基于时间清理旧数据
            if now - self._last_cleanup_time > self._cleanup_interval:
                self._cleanup_old_entries()
                self._last_cleanup_time = now
            
            return True
    
    def get_stats(self, key: str) -> Dict:
        """获取统计信息"""
        now = time.time()
        window_start = now - self.config.period_seconds
        queue = self.requests[key]
        
        # 清理过期请求
        while queue and queue[0] < window_start:
            queue.popleft()
        
        return {
            'current_requests': len(queue),
            'limit': self.config.requests,
            'period_seconds': self.config.period_seconds,
            'remaining': self.config.requests - len(queue)
        }


class TokenBucketRateLimiter:
    """令牌桶限流器"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.tokens: Dict[str, float] = defaultdict(float)
        self.last_refill_time: Dict[str, float] = defaultdict(time.time)
        self._lock = asyncio.Lock()
        self._last_cleanup_time = 0.0
        self._cleanup_interval = 30.0  # 每30秒至少清理一次
        
        # 初始填充
        self.capacity = config.burst_size or config.requests
        self.refill_rate = config.requests / config.period_seconds
    
    def _cleanup_old_entries(self):
        """清理长时间未使用的键，防止内存泄漏"""
        now = time.time()
        # 清理超过 2 个周期未使用的键
        cutoff_time = now - (self.config.period_seconds * 2)
        
        keys_to_remove = []
        for key in self.last_refill_time.keys():
            if self.last_refill_time[key] < cutoff_time:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.tokens[key]
            del self.last_refill_time[key]
    
    async def acquire(self, key: str, tokens: float = 1.0) -> bool:
        """
        获取令牌
        
        Args:
            key: 限流键
            tokens: 需要的令牌数
        
        Returns:
            是否允许通过
        """
        now = time.time()
        
        async with self._lock:
            # 先补充令牌
            time_since_last_refill = now - self.last_refill_time[key]
            tokens_to_add = time_since_last_refill * self.refill_rate
            self.tokens[key] = min(self.capacity, self.tokens[key] + tokens_to_add)
            self.last_refill_time[key] = now
            
            # 检查是否有足够的令牌
            if self.tokens[key] >= tokens:
                self.tokens[key] -= tokens
                
                # 基于时间清理旧数据
                if now - self._last_cleanup_time > self._cleanup_interval:
                    self._cleanup_old_entries()
                    self._last_cleanup_time = now
                
                return True
            else:
                logger.warning(
                    f"Token bucket rate limit exceeded for key: {key} (current: {self.tokens[key]:.2f}, required: {tokens})"
                )
                return False
    
    def get_stats(self, key: str) -> Dict:
        """获取统计信息"""
        now = time.time()
        
        # 计算当前令牌数（不真正更新）
        time_since_last_refill = now - self.last_refill_time[key]
        tokens_to_add = time_since_last_refill * self.refill_rate
        current_tokens = min(self.capacity, self.tokens.get(key, 0) + tokens_to_add)
        
        return {
            'current_tokens': current_tokens,
            'capacity': self.capacity,
            'refill_rate': self.refill_rate,
            'remaining': current_tokens
        }


class FixedWindowRateLimiter:
    """固定窗口限流器"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.window_counts: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        self._lock = asyncio.Lock()
        self._last_cleanup_time = 0.0
        self._cleanup_interval = 30.0  # 每30秒至少清理一次
    
    def _get_window_key(self, now: float) -> int:
        """获取窗口键"""
        window_size = self.config.period_seconds
        return int(now // window_size)

    def _cleanup_old_windows(self):
        """清理过期的窗口数据，防止内存泄漏"""
        now = time.time()
        current_window_key = self._get_window_key(now)
        # 保留最近 3 个窗口的数据
        cutoff_window_key = current_window_key - 3

        keys_to_remove = []
        for key, windows in self.window_counts.items():
            windows_to_remove = [w for w in windows.keys() if w < cutoff_window_key]
            for w in windows_to_remove:
                del windows[w]

            # 如果某个 key 的所有窗口都被清理，删除该 key
            if not windows:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.window_counts[key]

    async def acquire(self, key: str) -> bool:
        """
        获取令牌
        
        Args:
            key: 限流键
        
        Returns:
            是否允许通过
        """
        now = time.time()
        window_key = self._get_window_key(now)
        
        async with self._lock:
            current_count = self.window_counts[key][window_key]

            if current_count >= self.config.requests:
                logger.warning(
                    f"Fixed window rate limit exceeded for key: {key} (current: {current_count}, limit: {self.config.requests})"
                )
                return False

            self.window_counts[key][window_key] += 1

            # 基于时间或请求数清理旧窗口
            total_requests = sum(sum(windows.values()) for windows in self.window_counts.values())
            if (total_requests % 100 == 0) or (now - self._last_cleanup_time > self._cleanup_interval):
                self._cleanup_old_windows()
                self._last_cleanup_time = now

            return True
    
    def get_stats(self, key: str) -> Dict:
        """获取统计信息"""
        now = time.time()
        window_key = self._get_window_key(now)
        current_count = self.window_counts[key][window_key]
        
        return {
            'current_count': current_count,
            'limit': self.config.requests,
            'period_seconds': self.config.period_seconds,
            'window_end': (window_key + 1) * self.config.period_seconds,
            'remaining': self.config.requests - current_count
        }


class RateLimiterManager:
    """限流器管理器"""
    
    _instance = None
    _limiters: Dict[str, object] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self._lock = asyncio.Lock()
    
    def register_limiter(
        self,
        name: str,
        limiter_type: str = 'sliding_window',
        requests: int = 100,
        period_seconds: float = 60.0,
        burst_size: Optional[int] = None
    ):
        """
        注册限流器
        
        Args:
            name: 限流器名称
            limiter_type: 限流器类型 ('sliding_window', 'token_bucket', 'fixed_window')
            requests: 请求数限制
            period_seconds: 周期（秒）
            burst_size: 突发大小
        """
        config = RateLimitConfig(
            requests=requests,
            period_seconds=period_seconds,
            burst_size=burst_size
        )
        
        if limiter_type == 'sliding_window':
            limiter = SlidingWindowRateLimiter(config)
        elif limiter_type == 'token_bucket':
            limiter = TokenBucketRateLimiter(config)
        elif limiter_type == 'fixed_window':
            limiter = FixedWindowRateLimiter(config)
        else:
            raise ValueError(f"Unknown limiter type: {limiter_type}")
        
        self._limiters[name] = limiter
        logger.info(f"Rate limiter '{name}' registered (type: {limiter_type})")
    
    async def acquire(self, limiter_name: str, key: str, **kwargs) -> bool:
        """
        获取令牌
        
        Args:
            limiter_name: 限流器名称
            key: 限流键
            **kwargs: 额外参数
        
        Returns:
            是否允许通过
        """
        limiter = self._limiters.get(limiter_name)
        if limiter is None:
            logger.warning(f"Rate limiter '{limiter_name}' not found, allowing request")
            return True
        
        return await limiter.acquire(key, **kwargs)
    
    def get_stats(self, limiter_name: str, key: str) -> Optional[Dict]:
        """获取统计信息"""
        limiter = self._limiters.get(limiter_name)
        if limiter is None:
            return None
        
        return limiter.get_stats(key)
    
    def list_limiters(self) -> Dict[str, Dict]:
        """列出所有限流器"""
        result = {}
        for name, limiter in self._limiters.items():
            result[name] = {
                'type': type(limiter).__name__
            }
        return result


# 全局单例
_rate_limiter_manager = RateLimiterManager()


def get_rate_limiter_manager() -> RateLimiterManager:
    """获取限流器管理器"""
    return _rate_limiter_manager


def rate_limit(
    limiter_name: str,
    key_func: callable = lambda *args, **kwargs: 'default',
    on_reject: Optional[callable] = None,
):
    """
    限流装饰器
    
    Args:
        limiter_name: 限流器名称
        key_func: 生成限流键的函数
        on_reject: 被拒绝时的回调
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            manager = get_rate_limiter_manager()
            key = key_func(*args, **kwargs)
            
            allowed = await manager.acquire(limiter_name, key)
            
            if not allowed:
                if on_reject is not None:
                    return on_reject(*args, **kwargs)
                raise RateLimitExceededError(f"Rate limit exceeded for {limiter_name}")
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


class RateLimitExceededError(Exception):
    """超出限流错误"""
    pass
