#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高性能 LRU 缓存实现
支持 TTL、统计、缓存策略优化
"""
import time
import hashlib
from typing import Any, Optional, Callable, Dict, List, Tuple
from collections import OrderedDict
from dataclasses import dataclass, field
from functools import wraps
import logging
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class LRUCacheEntry:
    """LRU缓存条目"""
    value: Any
    created_at: float
    ttl: int
    hit_count: int = 0
    last_accessed: float = field(default_factory=time.time)


class LRUCache:
    """
    线程安全的 LRU (Least Recently Used) 缓存
    
    特性:
    - 自动淘汰最久未使用的条目
    - 支持 TTL (Time To Live)
    - 支持缓存统计
    - 支持异步操作
    """
    
    def __init__(
        self,
        max_size: int = 10000,
        default_ttl: int = 3600,  # 默认1小时
        cleanup_threshold: float = 0.8
    ):
        """
        初始化LRU缓存
        
        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认过期时间(秒)
            cleanup_threshold: 清理阈值(当达到max_size*threshold时触发清理)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cleanup_threshold = cleanup_threshold
        
        # 使用OrderedDict实现LRU
        self._cache: OrderedDict[str, LRUCacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()
        
        # 统计信息
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._total_sets = 0
        
    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，如果未命中或过期则返回None
        """
        async with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
                
            entry = self._cache[key]
            
            # 检查是否过期
            if time.time() > entry.created_at + entry.ttl:
                del self._cache[key]
                self._misses += 1
                return None
                
            # 更新访问时间和命中计数
            entry.last_accessed = time.time()
            entry.hit_count += 1
            self._cache.move_to_end(key)  # 移到末尾表示最近使用
            
            self._hits += 1
            return entry.value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间(秒)，使用默认值如果为None
        """
        async with self._lock:
            ttl = ttl or self.default_ttl
            
            # 如果key已存在，先删除
            if key in self._cache:
                del self._cache[key]
            
            # 检查是否需要清理
            if len(self._cache) >= self.max_size * self.cleanup_threshold:
                self._evict_old_entries()
            
            # 添加新条目
            self._cache[key] = LRUCacheEntry(
                value=value,
                created_at=time.time(),
                ttl=ttl,
                last_accessed=time.time()
            )
            
            self._total_sets += 1
    
    async def delete(self, key: str) -> bool:
        """
        删除缓存条目
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功删除
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def clear(self) -> None:
        """清空所有缓存"""
        async with self._lock:
            self._cache.clear()
            logger.info("🧹 LRU缓存已清空")
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            统计字典
        """
        async with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self._hits,
                'misses': self._misses,
                'total_sets': self._total_sets,
                'evictions': self._evictions,
                'hit_rate': round(hit_rate, 2),
                'miss_rate': round(100 - hit_rate, 2)
            }
    
    def _evict_old_entries(self) -> None:
        """淘汰最旧的条目"""
        # 先清理过期条目
        current_time = time.time()
        expired_keys = [
            k for k, v in self._cache.items()
            if current_time > v.created_at + v.ttl
        ]
        
        for k in expired_keys:
            del self._cache[k]
            self._evictions += 1
        
        # 如果还需要清理，删除最旧的条目
        while len(self._cache) >= self.max_size:
            if self._cache:
                self._cache.popitem(last=False)  # 删除最旧的条目
                self._evictions += 1


# 全局LRU缓存实例
_lru_cache_instance: Optional[LRUCache] = None


def get_lru_cache(
    max_size: int = 10000,
    default_ttl: int = 3600
) -> LRUCache:
    """
    获取或创建全局LRU缓存实例
    
    Args:
        max_size: 最大缓存条目数
        default_ttl: 默认过期时间
        
    Returns:
        LRUCache实例
    """
    global _lru_cache_instance
    if _lru_cache_instance is None:
        _lru_cache_instance = LRUCache(max_size=max_size, default_ttl=default_ttl)
    return _lru_cache_instance


def lru_cache_decorator(
    ttl: int = 3600,
    max_size: int = 10000,
    key_prefix: str = ""
):
    """
    LRU缓存装饰器
    
    Args:
        ttl: 缓存过期时间(秒)
        max_size: 最大缓存条目数
        key_prefix: 键前缀
        
    Returns:
        装饰器函数
    """
    cache = get_lru_cache(max_size=max_size)
    
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 生成缓存键
            key_parts = [key_prefix or func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # 尝试从缓存获取
            cached = await cache.get(cache_key)
            if cached is not None:
                return cached
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 缓存结果
            await cache.set(cache_key, result, ttl)
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 生成缓存键
            key_parts = [key_prefix or func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # 使用同步方式获取/设置缓存
            loop = asyncio.get_event_loop()
            cached = loop.run_until_complete(cache.get(cache_key))
            if cached is not None:
                return cached
            
            result = func(*args, **kwargs)
            loop.run_until_complete(cache.set(cache_key, result, ttl))
            return result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
