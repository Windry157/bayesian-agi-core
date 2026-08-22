"""
缓存装饰器 - 便捷地为函数添加缓存功能
"""
import asyncio
import hashlib
import json
from functools import wraps
from typing import Any, Callable, Optional
import logging

logger = logging.getLogger(__name__)

def cached(
    cache_manager,
    prefix: str = "cache",
    ttl: Optional[int] = None,
    key_builder: Optional[Callable] = None
):
    """
    缓存装饰器
    
    Args:
        cache_manager: 缓存管理器实例
        prefix: 缓存键前缀
        ttl: 缓存过期时间(秒)，默认使用管理器的配置
        key_builder: 自定义键生成函数
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not cache_manager:
                return await func(*args, **kwargs)
                
            try:
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    key_data = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
                    cache_key = f"{prefix}:{hashlib.md5(key_data.encode()).hexdigest()}"
                    
                cached_value = await cache_manager.get(cache_key)
                if cached_value is not None:
                    return cached_value
                    
                result = await func(*args, **kwargs)
                
                await cache_manager.set(cache_key, result, ttl)
                
                return result
                
            except Exception as e:
                logger.warning(f"⚠️ 缓存装饰器执行失败: {e}, 直接执行原函数")
                return await func(*args, **kwargs)
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not cache_manager:
                return func(*args, **kwargs)
                
            try:
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    key_data = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
                    cache_key = f"{prefix}:{hashlib.md5(key_data.encode()).hexdigest()}"
                    
                loop = asyncio.get_event_loop()
                cached_value = loop.run_until_complete(cache_manager.get(cache_key))
                if cached_value is not None:
                    return cached_value
                    
                result = func(*args, **kwargs)
                
                loop.run_until_complete(cache_manager.set(cache_key, result, ttl))
                
                return result
                
            except Exception as e:
                logger.warning(f"⚠️ 缓存装饰器执行失败: {e}, 直接执行原函数")
                return func(*args, **kwargs)
                
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator
