import pytest
from src.mcp.search import TfidfIndex
from src.mcp.common import tokenize, cosine_similarity


class TestTokenize:
    def test_basic_tokenization(self):
        tokens = tokenize("hello world")
        assert len(tokens) > 0
        assert "hello" in tokens
        assert "world" in tokens

    def test_chinese_tokenization(self):
        tokens = tokenize("你好世界")
        assert len(tokens) > 0

    def test_ngram_generation(self):
        tokens = tokenize("ab", ngram_range=(2, 2))
        assert "ab" in tokens


class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = {"a": 1.0, "b": 2.0}
        assert cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        a = {"a": 1.0}
        b = {"b": 1.0}
        assert cosine_similarity(a, b) == 0.0

    def test_empty_vector(self):
        assert cosine_similarity({}, {"a": 1.0}) == 0.0


class TestTfidfIndex:
    def test_add_and_search(self):
        idx = TfidfIndex()
        idx.add_document({"id": "1", "content": "hello world"})
        idx.add_document({"id": "2", "content": "foo bar"})
        results = idx.search("hello", top_k=5)
        assert len(results) >= 1
        assert results[0][0] == 0

    def test_remove_document(self):
        idx = TfidfIndex()
        did = idx.add_document({"id": "1", "content": "test"})
        idx.remove_document(did)
        results = idx.search("test")
        assert len(results) == 0

    def test_snapshot(self):
        idx = TfidfIndex()
        idx.add_document({"id": "1", "content": "hello"})
        snap = idx.snapshot()
        assert snap["total_documents"] == 1
        assert snap["total_documents"] == 1
