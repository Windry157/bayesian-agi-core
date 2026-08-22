import json
import logging
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RedisCacheManager:
    def __init__(self, redis_url: Optional[str] = None):
        self._redis = None
        self._redis_url = redis_url

    async def connect(self):
        if not self._redis_url:
            return
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
            await self._redis.ping()
            logger.info(f"RedisCacheManager: connected ({self._redis_url})")
        except Exception as e:
            logger.warning(f"RedisCacheManager: connection failed ({e})")

    async def disconnect(self):
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    @property
    def available(self) -> bool:
        return self._redis is not None

    async def get(self, key: str, default: Any = None) -> Any:
        if not self._redis:
            return default
        try:
            val = await self._redis.get(key)
            if val is None:
                return default
            return json.loads(val)
        except Exception as e:
            logger.warning(f"Redis cache get error: {e}")
            return default

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        if not self._redis:
            return False
        try:
            await self._redis.setex(key, ttl, json.dumps(value, ensure_ascii=False))
            return True
        except Exception as e:
            logger.warning(f"Redis cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        if not self._redis:
            return False
        try:
            await self._redis.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Redis cache delete error: {e}")
            return False

    async def clear_pattern(self, pattern: str):
        if not self._redis:
            return
        try:
            cursor = 0
            while True:
                cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
                if keys:
                    await self._redis.delete(*keys)
                if cursor == 0:
                    break
        except Exception as e:
            logger.warning(f"Redis cache clear_pattern error: {e}")


redis_cache = RedisCacheManager()
