#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
置信度缓存模块
提供置信度评分的缓存和异步处理功能
"""

import logging
import hashlib
import json
import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from collections import OrderedDict
from dataclasses import dataclass, field

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at


class ConfidenceCache:
    """置信度缓存
    
    提供LRU缓存和TTL过期机制，用于加速置信度评分计算
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """初始化置信度缓存
        
        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认TTL（秒）
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._async_tasks: Dict[str, asyncio.Task] = {}
        
        logger.info(f"置信度缓存初始化完成: max_size={max_size}, default_ttl={default_ttl}s")

    def _generate_key(self, input_data: Dict[str, Any]) -> str:
        """生成缓存键
        
        Args:
            input_data: 输入数据
            
        Returns:
            缓存键
        """
        sorted_data = json.dumps(input_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(sorted_data.encode()).hexdigest()[:16]

    def get(self, input_data: Dict[str, Any]) -> Optional[Any]:
        """获取缓存值
        
        Args:
            input_data: 输入数据
            
        Returns:
            缓存值，如果不存在或过期返回None
        """
        key = self._generate_key(input_data)
        
        if key in self._cache:
            entry = self._cache[key]
            
            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                logger.debug(f"缓存过期: {key}")
                return None
            
            self._cache.move_to_end(key)
            entry.access_count += 1
            entry.last_accessed = datetime.now()
            
            self._hits += 1
            logger.debug(f"缓存命中: {key}, 访问次数: {entry.access_count}")
            return entry.value
        
        self._misses += 1
        logger.debug(f"缓存未命中: {key}")
        return None

    def set(self, input_data: Dict[str, Any], value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值
        
        Args:
            input_data: 输入数据
            value: 缓存值
            ttl: TTL（秒），None使用默认值
        """
        key = self._generate_key(input_data)
        
        if len(self._cache) >= self.max_size and key not in self._cache:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            logger.debug(f"缓存淘汰: {oldest_key}")
        
        expires_at = None
        if ttl is None:
            ttl = self.default_ttl
        
        if ttl > 0:
            expires_at = datetime.now() + timedelta(seconds=ttl)
        
        self._cache[key] = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            expires_at=expires_at
        )
        
        self._cache.move_to_end(key)
        
        logger.debug(f"缓存设置: {key}, TTL={ttl}s")

    def invalidate(self, input_data: Dict[str, Any]) -> bool:
        """使缓存失效
        
        Args:
            input_data: 输入数据
            
        Returns:
            是否成功使缓存失效
        """
        key = self._generate_key(input_data)
        
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"缓存失效: {key}")
            return True
        
        return False

    def clear(self) -> int:
        """清空缓存
        
        Returns:
            清空的条目数
        """
        count = len(self._cache)
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        logger.info(f"缓存已清空: {count} 条目")
        return count

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计
        
        Returns:
            缓存统计信息
        """
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0
        
        total_access_count = sum(entry.access_count for entry in self._cache.values())
        avg_access_count = total_access_count / len(self._cache) if self._cache else 0
        
        expired_count = sum(1 for entry in self._cache.values() if entry.is_expired())
        
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate * 100, 2),
            "total_requests": total_requests,
            "avg_access_count": round(avg_access_count, 2),
            "expired_count": expired_count,
            "default_ttl": self.default_ttl
        }

    def cleanup_expired(self) -> int:
        """清理过期条目
        
        Returns:
            清理的条目数
        """
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.info(f"清理过期缓存: {len(expired_keys)} 条目")
        
        return len(expired_keys)


class AsyncConfidenceProcessor:
    """异步置信度处理器
    
    提供置信度评分的异步处理能力
    支持任务取消、进度跟踪和结果回调
    """

    def __init__(self, max_concurrent: int = 5):
        """初始化异步置信度处理器
        
        Args:
            max_concurrent: 最大并发任务数
        """
        self.max_concurrent = max_concurrent
        self._tasks: Dict[str, asyncio.Task] = {}
        self._results: Dict[str, Any] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
        logger.info(f"异步置信度处理器初始化完成: max_concurrent={max_concurrent}")

    async def process_with_semaphore(
        self,
        task_id: str,
        coro: Callable
    ) -> Any:
        """使用信号量限制并发
        
        Args:
            task_id: 任务ID
            coro: 协程
            
        Returns:
            处理结果
        """
        async with self._semaphore:
            logger.debug(f"任务开始: {task_id}")
            result = await coro
            self._results[task_id] = result
            logger.debug(f"任务完成: {task_id}")
            return result

    async def submit_task(
        self,
        task_id: str,
        coro: Callable
    ) -> asyncio.Task:
        """提交异步任务
        
        Args:
            task_id: 任务ID
            coro: 协程
            
        Returns:
            异步任务
        """
        task = asyncio.create_task(self.process_with_semaphore(task_id, coro))
        self._tasks[task_id] = task
        
        logger.info(f"任务已提交: {task_id}")
        
        def task_done_callback(t):
            if task_id in self._tasks:
                del self._tasks[task_id]
            logger.debug(f"任务已移除: {task_id}")
        
        task.add_done_callback(task_done_callback)
        
        return task

    async def get_result(self, task_id: str, timeout: Optional[float] = None) -> Optional[Any]:
        """获取任务结果
        
        Args:
            task_id: 任务ID
            timeout: 超时时间（秒）
            
        Returns:
            任务结果
        """
        if task_id not in self._tasks:
            return self._results.get(task_id)
        
        task = self._tasks[task_id]
        
        try:
            result = await asyncio.wait_for(task, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            logger.warning(f"任务超时: {task_id}, timeout={timeout}s")
            return None
        except asyncio.CancelledError:
            logger.info(f"任务已取消: {task_id}")
            return None

    def cancel_task(self, task_id: str) -> bool:
        """取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功取消
        """
        if task_id in self._tasks:
            self._tasks[task_id].cancel()
            logger.info(f"任务已取消: {task_id}")
            return True
        
        return False

    def cancel_all(self) -> int:
        """取消所有任务
        
        Returns:
            取消的任务数
        """
        count = len(self._tasks)
        for task in self._tasks.values():
            task.cancel()
        
        logger.info(f"已取消所有任务: {count} 个")
        return count

    def get_pending_tasks(self) -> List[str]:
        """获取待处理任务列表
        
        Returns:
            待处理任务ID列表
        """
        return list(self._tasks.keys())

    def get_stats(self) -> Dict[str, Any]:
        """获取处理器统计
        
        Returns:
            统计信息
        """
        return {
            "max_concurrent": self.max_concurrent,
            "pending_tasks": len(self._tasks),
            "completed_results": len(self._results)
        }


class ConfidenceCacheManager:
    """置信度缓存管理器
    
    整合缓存和异步处理，提供便捷的置信度评分接口
    """

    def __init__(
        self,
        max_cache_size: int = 1000,
        cache_ttl: int = 3600,
        max_concurrent: int = 5
    ):
        """初始化缓存管理器
        
        Args:
            max_cache_size: 最大缓存大小
            cache_ttl: 缓存TTL
            max_concurrent: 最大并发数
        """
        self.cache = ConfidenceCache(max_size=max_cache_size, default_ttl=cache_ttl)
        self.async_processor = AsyncConfidenceProcessor(max_concurrent=max_concurrent)
        
        logger.info("置信度缓存管理器初始化完成")

    async def get_cached_or_compute(
        self,
        input_data: Dict[str, Any],
        compute_func: Callable,
        ttl: Optional[int] = None
    ) -> Any:
        """获取缓存或计算
        
        Args:
            input_data: 输入数据
            compute_func: 计算函数
            ttl: 缓存TTL
            
        Returns:
            结果
        """
        cached_result = self.cache.get(input_data)
        
        if cached_result is not None:
            return cached_result
        
        result = await compute_func()
        
        self.cache.set(input_data, result, ttl)
        
        return result

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息
        
        Returns:
            统计信息
        """
        return {
            "cache": self.cache.get_stats(),
            "async_processor": self.async_processor.get_stats()
        }


# 全局缓存管理器实例
confidence_cache_manager = ConfidenceCacheManager()