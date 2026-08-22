import pytest
from src.mcp.bug_db import BugDatabase


class TestBugDatabase:
    @pytest.fixture
    def db(self, tmp_path):
        return BugDatabase(tmp_path)

    def test_add_bug(self, db):
        bug = db.add_bug({"description": "test bug", "language": "python", "severity": "critical"})
        assert bug["id"].startswith("BUG-")
        assert bug["created_at"] is not None

    def test_search_empty(self, db):
        results = db.search("test")
        assert results == []

    def test_add_and_search(self, db):
        db.add_bug({"description": "null pointer exception", "language": "java", "severity": "critical"})
        db.add_bug({"description": "memory leak in loop", "language": "python", "severity": "high"})
        results = db.search("null pointer", top_k=5)
        assert len(results) >= 1

    def test_search_with_language_filter(self, db):
        db.add_bug({"description": "python error", "language": "python", "severity": "high"})
        db.add_bug({"description": "java error", "language": "java", "severity": "high"})
        results = db.search("error", top_k=5, filters={"language": "python"})
        assert all(r["language"] == "python" for r in results)

    def test_search_with_severity_filter(self, db):
        db.add_bug({"description": "critical bug", "language": "python", "severity": "critical"})
        db.add_bug({"description": "minor bug", "language": "python", "severity": "low"})
        results = db.search("bug", top_k=5, filters={"severity": "critical"})
        assert all(r["severity"] == "critical" for r in results)

    def test_get_stats_empty(self, db):
        stats = db.get_stats()
        assert stats["total_bugs"] == 0

    def test_get_stats_with_bugs(self, db):
        db.add_bug({"description": "bug1", "language": "python"})
        db.add_bug({"description": "bug2", "language": "java"})
        stats = db.get_stats()
        assert stats["total_bugs"] == 2

    def test_relevance_score(self, db):
        db.add_bug({"description": "python memory leak critical"})
        results = db.search("memory leak", top_k=5)
        if results:
            assert "relevance_score" in results[0]
            assert 0 <= results[0]["relevance_score"] <= 1
