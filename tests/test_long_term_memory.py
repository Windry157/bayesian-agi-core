import pytest
from collections import OrderedDict
from src.core.memory.long_term_memory import LongTermMemory


class DummyLongTermMemory(LongTermMemory):
    def __init__(self):
        # 避免真实数据库连接
        self.host = "localhost"
        self.port = 5432
        self.database = "bayesian_agi"
        self.user = "postgres"
        self.password = "postgres"
        self.min_connections = 1
        self.max_connections = 1
        self.connection_pool = None
        self.cache = OrderedDict()
        self.cache_size = 3

    def _create_connection_pool(self):
        return None

    def _create_tables(self):
        return None

    def _get_connection(self):
        return None

    def _put_connection(self, conn):
        return None


def test_update_cache_evicts_least_recently_used():
    memory = DummyLongTermMemory()

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
    memory = DummyLongTermMemory()
    memory._update_cache("a", "content_a")
    memory._update_cache("b", "content_b")
    memory._update_cache("c", "content_c")

    memory._update_cache("b", "content_b_updated")

    assert len(memory.cache) == 3
    assert memory.cache["b"]["content"] == "content_b_updated"
    assert list(memory.cache.keys()) == ["a", "c", "b"]
