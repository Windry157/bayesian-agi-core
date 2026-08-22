import pytest
from src.mcp.code_analyzer import CodeAnalyzer


class TestCodeAnalyzer:
    @pytest.fixture
    def analyzer(self):
        return CodeAnalyzer()

    def test_cyclomatic_simple(self, analyzer):
        code = "def foo(): pass"
        assert analyzer.cyclomatic_complexity(code) == 1

    def test_cyclomatic_with_branches(self, analyzer):
        code = """
def foo(x):
    if x > 0:
        return 1
    else:
        return 2
"""
        assert analyzer.cyclomatic_complexity(code) >= 2

    def test_cognitive_complexity(self, analyzer):
        code = "def foo():\n    if x:\n        if y:\n            pass"
        assert analyzer.cognitive_complexity(code) > 0

    def test_halstead_metrics(self, analyzer):
        code = "def add(a, b): return a + b"
        metrics = analyzer.halstead_metrics(code)
        assert metrics["vocabulary"] > 0
        assert metrics["volume"] > 0

    def test_halstead_empty(self, analyzer):
        metrics = analyzer.halstead_metrics("")
        assert metrics["vocabulary"] == 0

    def test_detect_infinite_loop(self, analyzer):
        code = "while True:\n    pass"
        issues = analyzer.detect_issues(code)
        types = [i["type"] for i in issues]
        assert "infinite_loop" in types

    def test_detect_missing_error_handling(self, analyzer):
        code = "def read_file():\n    f = open('test.txt')\n    return f.read()"
        issues = analyzer.detect_issues(code)
        types = [i["type"] for i in issues]
        assert "missing_error_handling" in types

    def test_detect_hardcoded_secret(self, analyzer):
        code = 'password = "super_secret_123"'
        issues = analyzer.detect_issues(code)
        types = [i["type"] for i in issues]
        assert "hardcoded_secret" in types

    def test_detect_sql_injection(self, analyzer):
        code = 'cursor.execute("SELECT * FROM users WHERE id = " + user_id)'
        issues = analyzer.detect_issues(code)
        types = [i["type"] for i in issues]
        assert "sql_injection" in types

    def test_no_false_positives(self, analyzer):
        code = "def add(a, b): return a + b"
        issues = analyzer.detect_issues(code)
        assert len(issues) == 0
