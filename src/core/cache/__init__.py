"""
缓存模块 - 提供 Redis 缓存支持，提升系统性能
"""
from .cache_manager import CacheManager, CacheConfig
from .cache_decorator import cached
from .metrics import CacheMetrics

__all__ = ['CacheManager', 'CacheConfig', 'cached', 'CacheMetrics']
