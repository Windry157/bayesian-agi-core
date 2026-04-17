#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据缓存模块
负责管理数据的缓存，减少数据库查询和文件读取
"""

import time
import threading
from typing import Dict, Optional, Any


class DataCache:
    """数据缓存

    管理数据的缓存，减少数据库查询和文件读取
    """

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """初始化数据缓存

        Args:
            max_size: 缓存的最大大小
            ttl: 缓存的过期时间（秒）
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_times: Dict[str, float] = {}
        self.lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存的数据

        Args:
            key: 数据的键

        Returns:
            缓存的数据，如果不存在或已过期返回None
        """
        with self.lock:
            if key in self.cache:
                # 检查是否过期
                ttl = self.cache[key].get("ttl", self.ttl)
                if time.time() - self.cache[key]["timestamp"] < ttl:
                    # 更新访问时间
                    self.access_times[key] = time.time()
                    return self.cache[key]["data"]
                else:
                    # 删除过期的数据
                    del self.cache[key]
                    del self.access_times[key]
            return None

    def set(self, key: str, data: Any, metadata: Optional[Dict[str, Any]] = None, ttl: Optional[int] = None):
        """设置缓存的数据

        Args:
            key: 数据的键
            data: 数据对象
            metadata: 数据的元数据
            ttl: 缓存的过期时间（秒），如果不指定则使用默认值
        """
        with self.lock:
            # 如果缓存已满，删除最旧的数据线
            if len(self.cache) >= self.max_size and key not in self.cache:
                oldest_key = min(self.access_times, key=self.access_times.get)
                del self.cache[oldest_key]
                del self.access_times[oldest_key]

            # 设置缓存
            self.cache[key] = {
                "data": data,
                "metadata": metadata or {},
                "timestamp": time.time(),
                "ttl": ttl if ttl is not None else self.ttl,
            }
            self.access_times[key] = time.time()

    def delete(self, key: str):
        """删除缓存的数据

        Args:
            key: 数据的键
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                del self.access_times[key]

    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()

    def get_size(self) -> int:
        """获取缓存的大小

        Returns:
            缓存的大小
        """
        with self.lock:
            return len(self.cache)

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存的统计信息

        Returns:
            缓存的统计信息
        """
        with self.lock:
            stats = {
                "size": len(self.cache),
                "max_size": self.max_size,
                "ttl": self.ttl,
                "keys": list(self.cache.keys()),
                "access_times": self.access_times.copy(),
            }
            return stats

    def clean_expired(self):
        """清理过期的数据"""
        with self.lock:
            expired_keys = []
            current_time = time.time()

            for key, cache_entry in self.cache.items():
                ttl = cache_entry.get("ttl", self.ttl)
                if current_time - cache_entry["timestamp"] >= ttl:
                    expired_keys.append(key)

            for key in expired_keys:
                del self.cache[key]
                del self.access_times[key]


# 全局数据缓存实例
data_cache = DataCache()
