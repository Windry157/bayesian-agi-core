import pytest
from pathlib import Path
from src.mcp.insight import InsightGenerator
from src.mcp.memory import MemoryStore
from src.mcp.bug_db import BugDatabase


class TestInsightGenerator:
    @pytest.fixture
    def memory(self, tmp_path):
        return MemoryStore(tmp_path)

    @pytest.fixture
    def bug_db(self, tmp_path):
        return BugDatabase(tmp_path)

    def test_generate_basic(self, memory, bug_db):
        result = InsightGenerator.generate("test", memory, bug_db, depth="surface")
        assert result["topic"] == "test"
        assert result["depth"] == "surface"
        assert "insights" in result
        assert "patterns_identified" in result
        assert "recommendations" in result

    def test_generate_with_memory_data(self, memory, bug_db):
        memory.add("important critical bug fix", layer="short_term")
        result = InsightGenerator.generate("bug", memory, bug_db)
        assert len(result["insights"]) > 0
        assert result["data_sources"]["memory_matches"] > 0

    def test_generate_with_bug_data(self, memory, bug_db):
        bug_db.add_bug({"description": "critical security bug", "language": "python", "severity": "critical"})
        result = InsightGenerator.generate("security", memory, bug_db)
        assert result["data_sources"]["bug_matches"] > 0

    def test_confidence_scale(self, memory, bug_db):
        result = InsightGenerator.generate("test", memory, bug_db)
        assert 0 <= result["overall_confidence"] <= 1

    def test_recommendations_included(self, memory, bug_db):
        bug_db.add_bug({"description": "test bug", "language": "python", "severity": "high"})
        result = InsightGenerator.generate("test", memory, bug_db)
        assert len(result["recommendations"]) > 0
