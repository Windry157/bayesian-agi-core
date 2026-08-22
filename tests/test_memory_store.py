import pytest
from pathlib import Path
from src.mcp.memory import MemoryStore, MemoryItem


class TestMemoryStore:
    @pytest.fixture
    def store(self, tmp_path):
        return MemoryStore(tmp_path)

    def test_add_and_get(self, store):
        item = store.add("test content", layer="short_term")
        assert item.id is not None
        assert item.content == "test content"
        assert item.layer == "short_term"

        retrieved = store.get(item.id)
        assert retrieved is not None
        assert retrieved.id == item.id

    def test_get_nonexistent(self, store):
        assert store.get("nonexistent") is None

    def test_add_with_importance(self, store):
        item = store.add("important error bug fix critical", importance=0.9)
        assert item.importance == 0.9

    def test_add_default_layer(self, store):
        item = store.add("test", layer="invalid_layer")
        assert item.layer == "short_term"

    def test_search(self, store):
        store.add("hello world python code", layer="short_term")
        store.add("java javascript typescript", layer="medium_term")
        results = store.search("python", layers=["short_term", "medium_term"])
        assert len(results) >= 1

    def test_search_with_layer_filter(self, store):
        store.add("python code", layer="short_term")
        store.add("python article", layer="long_term")
        results = store.search("python", layers=["long_term"])
        assert all(r.layer == "long_term" for r, _ in results)

    def test_estimate_importance(self, store):
        imp = store._estimate_importance("this is a critical security vulnerability")
        assert imp > 0.65

    def test_get_stats(self, store):
        store.add("item1", layer="short_term")
        store.add("item2", layer="medium_term")
        stats = store.get_stats()
        assert stats["total_items"] == 2
        assert stats["short_term_count"] == 1
        assert stats["medium_term_count"] == 1

    def test_optimize_snapshot(self, store):
        result = store.optimize("snapshot")
        assert result["action_taken"] == "snapshot"

    def test_optimize_prune(self, store):
        for i in range(10):
            store.add(f"item{i}", importance=0.1)
        result = store.optimize("prune", {"min_importance": 0.5, "max_items": 1000})
        assert result["action_taken"] == "prune"

    def test_free_energy_empty_store(self, store):
        assert store._calculate_free_energy() == 0.0
