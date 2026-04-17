import pytest
from collections import OrderedDict
from src.core.memory.memory_system import MemorySystem


class DummyMemorySystem(MemorySystem):
    def __init__(self):
        # 避免真实文件操作
        super().__init__(memory_dir="./test_memory")
        self.cache = OrderedDict()
        self.cache_size = 3

    def _update_cache(self, key, content):
        """更新缓存"""
        if key in self.cache:
            # 更新现有键
            self.cache[key] = content
            # 移动到末尾表示最近使用
            self.cache.move_to_end(key)
        else:
            # 添加新键
            self.cache[key] = content
            # 如果超过缓存大小，删除最旧的
            if len(self.cache) > self.cache_size:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]


def test_update_cache_evicts_least_recently_used():
    memory = DummyMemorySystem()

    memory._update_cache("a", "content_a")
    memory._update_cache("b", "content_b")
    memory._update_cache("c", "content_c")

    assert list(memory.cache.keys()) == ["a", "b", "c"]

    # 访问 b，将 b 标记为最近使用
    memory.cache.move_to_end("b")

    memory._update_cache("d", "content_d")

    assert list(memory.cache.keys()) == ["c", "b", "d"]
    assert "a" not in memory.cache


def test_update_cache_updates_existing_key_without_evicting():
    memory = DummyMemorySystem()
    memory._update_cache("a", "content_a")
    memory._update_cache("b", "content_b")
    memory._update_cache("c", "content_c")

    memory._update_cache("b", "content_b_updated")

    assert len(memory.cache) == 3
    assert memory.cache["b"]["content"] == "content_b_updated"
    assert list(memory.cache.keys()) == ["a", "c", "b"]
