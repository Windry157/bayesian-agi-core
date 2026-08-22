#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推理引擎优化器
提供推理过程的性能优化和缓存
"""
import time
import hashlib
import asyncio
from typing import Any, Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from functools import wraps
import logging

logger = logging.getLogger(__name__)


@dataclass
class ReasoningCacheEntry:
    """推理缓存条目"""
    result: Any
    created_at: float
    computation_time: float
    hit_count: int = 0
    last_accessed: float = field(default_factory=time.time)


class ReasoningOptimizer:
    """
    推理引擎优化器
    
    功能:
    - 推理结果缓存
    - 计算时间统计
    - 推理路径优化
    - 热点推理识别
    """
    
    def __init__(
        self,
        cache_ttl: int = 300,  # 默认5分钟
        max_cache_size: int = 1000,
        enable_stats: bool = True
    ):
        self.cache_ttl = cache_ttl
        self.max_cache_size = max_cache_size
        self.enable_stats = enable_stats
        
        # 推理缓存
        self._cache: Dict[str, ReasoningCacheEntry] = {}
        self._lock = asyncio.Lock()
        
        # 统计信息
        self._total_inferences = 0
        self._cache_hits = 0
        self._total_compute_time = 0.0
        self._hot_inferences: Dict[str, int] = {}  # 推理类型 -> 调用次数
    
    async def cached_reasoning(
        self,
        reasoning_func: Callable,
        reasoning_type: str,
        *args,
        **kwargs
    ) -> Any:
        """
        带缓存的推理执行
        
        Args:
            reasoning_func: 推理函数
            reasoning_type: 推理类型标识
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            推理结果
        """
        # 生成缓存键
        cache_key = self._generate_cache_key(reasoning_type, *args, **kwargs)
        
        # 尝试从缓存获取
        cached = await self._get_from_cache(cache_key)
        if cached is not None:
            self._cache_hits += 1
            logger.debug(f"💾 推理缓存命中: {reasoning_type}")
            return cached
        
        # 执行推理
        start_time = time.time()
        result = await reasoning_func(*args, **kwargs) if asyncio.iscoroutinefunction(reasoning_func) else reasoning_func(*args, **kwargs)
        compute_time = time.time() - start_time
        
        # 更新统计
        self._total_inferences += 1
        self._total_compute_time += compute_time
        self._hot_inferences[reasoning_type] = self._hot_inferences.get(reasoning_type, 0) + 1
        
        # 缓存结果
        await self._set_to_cache(cache_key, result, compute_time)
        
        logger.debug(f"⚡ 推理完成: {reasoning_type}, 耗时: {compute_time:.3f}s")
        return result
    
    def _generate_cache_key(self, reasoning_type: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key_parts = [reasoning_type]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return hashlib.sha256(":".join(key_parts).encode()).hexdigest()
    
    async def _get_from_cache(self, key: str) -> Optional[Any]:
        """从缓存获取"""
        async with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            # 检查过期
            if time.time() - entry.created_at > self.cache_ttl:
                del self._cache[key]
                return None
            
            # 更新访问信息
            entry.hit_count += 1
            entry.last_accessed = time.time()
            
            return entry.result
    
    async def _set_to_cache(self, key: str, result: Any, compute_time: float) -> None:
        """设置缓存"""
        async with self._lock:
            # 检查缓存大小
            if len(self._cache) >= self.max_cache_size:
                self._cleanup_cache()
            
            self._cache[key] = ReasoningCacheEntry(
                result=result,
                created_at=time.time(),
                computation_time=compute_time
            )
    
    def _cleanup_cache(self) -> None:
        """清理缓存"""
        # 删除过期的
        current_time = time.time()
        expired_keys = [
            k for k, v in self._cache.items()
            if current_time - v.created_at > self.cache_ttl
        ]
        for k in expired_keys:
            del self._cache[k]
        
        # 如果还需要清理，删除最旧的
        if len(self._cache) >= self.max_cache_size:
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: x[1].last_accessed
            )
            to_remove = sorted_entries[:len(sorted_entries) // 2]
            for k, _ in to_remove:
                del self._cache[k]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取优化器统计信息"""
        avg_compute_time = (
            self._total_compute_time / self._total_inferences
            if self._total_inferences > 0
            else 0
        )
        cache_hit_rate = (
            self._cache_hits / (self._total_inferences + self._cache_hits) * 100
            if (self._total_inferences + self._cache_hits) > 0
            else 0
        )
        
        return {
            'total_inferences': self._total_inferences,
            'cache_hits': self._cache_hits,
            'cache_hit_rate': round(cache_hit_rate, 2),
            'cache_size': len(self._cache),
            'avg_compute_time': round(avg_compute_time, 4),
            'total_compute_time': round(self._total_compute_time, 2),
            'hot_inferences': dict(sorted(
                self._hot_inferences.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10])
        }
    
    async def clear_cache(self) -> None:
        """清空缓存"""
        async with self._lock:
            self._cache.clear()
            logger.info("🧹 推理缓存已清空")


# 全局优化器实例
_reasoning_optimizer: Optional[ReasoningOptimizer] = None


def get_reasoning_optimizer(
    cache_ttl: int = 300,
    max_cache_size: int = 1000
) -> ReasoningOptimizer:
    """获取或创建全局推理优化器"""
    global _reasoning_optimizer
    if _reasoning_optimizer is None:
        _reasoning_optimizer = ReasoningOptimizer(
            cache_ttl=cache_ttl,
            max_cache_size=max_cache_size
        )
    return _reasoning_optimizer


def optimize_reasoning(
    reasoning_type: str,
    cache_ttl: int = 300
):
    """
    推理优化装饰器
    
    Args:
        reasoning_type: 推理类型标识
        cache_ttl: 缓存过期时间
    """
    optimizer = get_reasoning_optimizer(cache_ttl=cache_ttl)
    
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await optimizer.cached_reasoning(
                func,
                reasoning_type,
                *args,
                **kwargs
            )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(
                optimizer.cached_reasoning(func, reasoning_type, *args, **kwargs)
            )
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
