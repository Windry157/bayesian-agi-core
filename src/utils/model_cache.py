#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型缓存模块
负责管理模型的缓存，减少模型加载时间
"""

import time
import threading
from typing import Dict, Optional, Any


class ModelCache:
    """模型缓存
    
    管理模型的缓存，减少模型加载时间
    """
    
    def __init__(self, max_size: int = 10):
        """初始化模型缓存
        
        Args:
            max_size: 缓存的最大大小
        """
        self.max_size = max_size
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_times: Dict[str, float] = {}
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存的模型
        
        Args:
            key: 模型的键
            
        Returns:
            缓存的模型，如果不存在返回None
        """
        with self.lock:
            if key in self.cache:
                # 更新访问时间
                self.access_times[key] = time.time()
                return self.cache[key]["model"]
            return None
    
    def set(self, key: str, model: Any, metadata: Optional[Dict[str, Any]] = None):
        """设置缓存的模型
        
        Args:
            key: 模型的键
            model: 模型对象
            metadata: 模型的元数据
        """
        with self.lock:
            # 如果缓存已满，删除最旧的模型
            if len(self.cache) >= self.max_size and key not in self.cache:
                oldest_key = min(self.access_times, key=self.access_times.get)
                del self.cache[oldest_key]
                del self.access_times[oldest_key]
            
            # 设置缓存
            self.cache[key] = {
                "model": model,
                "metadata": metadata or {},
                "timestamp": time.time()
            }
            self.access_times[key] = time.time()
    
    def delete(self, key: str):
        """删除缓存的模型
        
        Args:
            key: 模型的键
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
                "keys": list(self.cache.keys()),
                "access_times": self.access_times.copy()
            }
            return stats


# 全局模型缓存实例
model_cache = ModelCache()