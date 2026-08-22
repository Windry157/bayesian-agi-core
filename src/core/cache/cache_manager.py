"""
缓存管理器 - 提供 Redis 和内存缓存支持
"""
import asyncio
import hashlib
import json
import time
from typing import Any, Optional, Callable, Dict
from functools import wraps
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

@dataclass
class CacheConfig:
    """缓存配置"""
    use_redis: bool = True
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    default_ttl: int = 3600  # 默认1小时
    max_memory_entries: int = 10000  # 内存缓存最大条目数

@dataclass
class CacheEntry:
    """缓存条目"""
    value: Any
    created_at: float
    ttl: int
    hit_count: int = 0

class CacheManager:
    """缓存管理器"""
    
    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._redis_client = None
        self._lock = asyncio.Lock()
        self._initialized = False
        
    async def initialize(self):
        """初始化缓存"""
        if self._initialized:
            return
            
        if self.config.use_redis:
            try:
                import redis
                self._redis_client = redis.Redis(
                    host=self.config.redis_host,
                    port=self.config.redis_port,
                    db=self.config.redis_db,
                    password=self.config.redis_password,
                    decode_responses=False
                )
                self._redis_client.ping()
                logger.info("✅ Redis 缓存连接成功")
            except Exception as e:
                logger.warning(f"⚠️ Redis 连接失败，使用内存缓存: {e}")
                self._redis_client = None
        else:
            logger.info("ℹ️ 配置使用内存缓存")
            
        self._initialized = True
        
    async def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = f"{prefix}:{str(args)}:{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()
        
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if not self._initialized:
            await self.initialize()
            
        try:
            if self._redis_client:
                data = self._redis_client.get(key)
                if data:
                    cached_data = json.loads(data)
                    if time.time() < cached_data['expires_at']:
                        logger.debug(f"🔄 Redis 缓存命中: {key[:20]}...")
                        return cached_data['value']
                    else:
                        self._redis_client.delete(key)
            else:
                if key in self._memory_cache:
                    entry = self._memory_cache[key]
                    if time.time() < entry.created_at + entry.ttl:
                        entry.hit_count += 1
                        logger.debug(f"🔄 内存缓存命中: {key[:20]}...")
                        return entry.value
                    else:
                        del self._memory_cache[key]
        except Exception as e:
            logger.warning(f"⚠️ 缓存读取失败: {e}")
            
        return None
        
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """设置缓存值"""
        if not self._initialized:
            await self.initialize()
            
        ttl = ttl or self.config.default_ttl
        expires_at = time.time() + ttl
        
        try:
            if self._redis_client:
                cache_data = {
                    'value': value,
                    'expires_at': expires_at,
                    'created_at': time.time()
                }
                self._redis_client.setex(
                    key,
                    ttl,
                    json.dumps(cache_data)
                )
                logger.debug(f"💾 Redis 缓存设置: {key[:20]}...")
            else:
                async with self._lock:
                    if len(self._memory_cache) >= self.config.max_memory_entries:
                        self._cleanup_memory_cache()
                    self._memory_cache[key] = CacheEntry(
                        value=value,
                        created_at=time.time(),
                        ttl=ttl
                    )
                    logger.debug(f"💾 内存缓存设置: {key[:20]}...")
        except Exception as e:
            logger.warning(f"⚠️ 缓存写入失败: {e}")
            
    async def delete(self, key: str):
        """删除缓存"""
        if not self._initialized:
            await self.initialize()
            
        try:
            if self._redis_client:
                self._redis_client.delete(key)
                logger.debug(f"🗑️ Redis 缓存删除: {key[:20]}...")
            else:
                if key in self._memory_cache:
                    del self._memory_cache[key]
                    logger.debug(f"🗑️ 内存缓存删除: {key[:20]}...")
        except Exception as e:
            logger.warning(f"⚠️ 缓存删除失败: {e}")
            
    async def delete_pattern(self, pattern: str):
        """批量删除匹配模式的缓存"""
        if not self._initialized:
            await self.initialize()
            
        try:
            if self._redis_client:
                keys = self._redis_client.keys(pattern)
                if keys:
                    self._redis_client.delete(*keys)
                    logger.info(f"🗑️ 批量删除 Redis 缓存: {len(keys)} 条")
            else:
                to_delete = [k for k in self._memory_cache.keys() if pattern in k]
                for k in to_delete:
                    del self._memory_cache[k]
                logger.info(f"🗑️ 批量删除内存缓存: {len(to_delete)} 条")
        except Exception as e:
            logger.warning(f"⚠️ 批量缓存删除失败: {e}")
            
    async def clear_all(self):
        """清空所有缓存"""
        if not self._initialized:
            await self.initialize()
            
        try:
            if self._redis_client:
                self._redis_client.flushdb()
                logger.info("🗑️ Redis 缓存已清空")
            else:
                self._memory_cache.clear()
                logger.info("🗑️ 内存缓存已清空")
        except Exception as e:
            logger.warning(f"⚠️ 缓存清空失败: {e}")
            
    async def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        if not self._initialized:
            await self.initialize()
            
        stats = {
            'cache_type': 'redis' if self._redis_client else 'memory',
            'memory_entries': len(self._memory_cache)
        }
        
        if self._redis_client:
            try:
                info = self._redis_client.info()
                stats['redis_keys'] = info.get('db0', {}).get('keys', 0)
                stats['redis_memory_used'] = info.get('used_memory_human', 'N/A')
                stats['redis_hits'] = info.get('keyspace_hits', 0)
                stats['redis_misses'] = info.get('keyspace_misses', 0)
            except Exception as e:
                logger.warning(f"⚠️ 获取 Redis 统计失败: {e}")
                
        return stats
        
    def _cleanup_memory_cache(self):
        """清理内存缓存（删除最旧的条目）"""
        sorted_entries = sorted(
            self._memory_cache.items(),
            key=lambda x: x[1].created_at
        )
        to_remove = sorted_entries[:len(sorted_entries) // 2]
        for k, _ in to_remove:
            del self._memory_cache[k]
        logger.debug(f"🧹 清理了 {len(to_remove)} 个内存缓存条目")
        
    async def close(self):
        """关闭缓存连接"""
        if self._redis_client:
            self._redis_client.close()
            logger.info("👋 Redis 连接已关闭")
        self._initialized = False
