import pytest
from src.utils.redis_cache import RedisCacheManager


class TestRedisCacheManager:
    @pytest.fixture
    def cache(self):
        return RedisCacheManager()

    @pytest.mark.asyncio
    async def test_available_without_redis(self, cache):
        assert cache.available is False

    @pytest.mark.asyncio
    async def test_get_default_on_miss(self, cache):
        result = await cache.get("nonexistent", default="fallback")
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_set_without_redis(self, cache):
        result = await cache.set("key", "value")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_without_redis(self, cache):
        result = await cache.delete("key")
        assert result is False
