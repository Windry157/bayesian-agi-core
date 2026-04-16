import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.main import app


class TestAPIEndpoints:
    """API端点集成测试"""

    def setup_method(self):
        """测试前设置"""
        self.client = TestClient(app)

    def test_health_endpoint(self):
        """测试健康检查端点"""
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "Bayesian-AGI-Core is running" in data["message"]

    def test_root_endpoint(self):
        """测试根端点"""
        response = self.client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Welcome to Bayesian-AGI-Core"
        assert data["version"] == "1.0.0"

    @patch('src.main.assistant.get_models')
    def test_models_endpoint(self, mock_get_models):
        """测试模型列表端点"""
        mock_get_models.return_value = [
            {"name": "deepseek-r1:7b", "provider": "ollama", "type": "local"}
        ]
        response = self.client.get("/api/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert len(data["models"]) == 1
        assert data["models"][0]["name"] == "deepseek-r1:7b"

    @patch('src.main.assistant.add_memory')
    def test_add_memory_endpoint(self, mock_add_memory):
        """测试添加记忆端点"""
        mock_add_memory.return_value = "mem_123"
        payload = {"content": "测试记忆内容"}
        response = self.client.post("/api/memory", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "mem_123"
        assert "Memory added successfully" in data["message"]

    @patch('src.main.assistant.retrieve_memories')
    def test_search_memory_endpoint(self, mock_retrieve_memories):
        """测试检索记忆端点"""
        mock_retrieve_memories.return_value = [
            {"id": "mem_123", "content": "测试记忆", "score": 0.95}
        ]
        response = self.client.get("/api/memory/search?query=test")
        assert response.status_code == 200
        data = response.json()
        assert "memories" in data
        assert len(data["memories"]) == 1
        assert data["memories"][0]["content"] == "测试记忆"

    @patch('src.main.assistant.make_decision')
    def test_decision_endpoint(self, mock_make_decision):
        """测试决策端点"""
        mock_make_decision.return_value = "action_1"
        payload = ["action_1", "action_2", "action_3"]
        response = self.client.post("/api/decision", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "action_1"


class TestErrorHandling:
    """错误处理测试"""

    def setup_method(self):
        """测试前设置"""
        self.client = TestClient(app)

    @patch('src.main.assistant.add_memory', side_effect=Exception("Database error"))
    def test_add_memory_error_handling(self, mock_add_memory):
        """测试添加记忆错误处理"""
        payload = {"content": "测试内容"}
        response = self.client.post("/api/memory", json=payload)
        assert response.status_code == 500
        data = response.json()
        assert "Failed to add memory" in data["detail"]

    @patch('src.main.assistant.retrieve_memories', side_effect=Exception("Search error"))
    def test_search_memory_error_handling(self, mock_retrieve_memories):
        """测试检索记忆错误处理"""
        response = self.client.get("/api/memory/search?query=test")
        assert response.status_code == 500
        data = response.json()
        assert "Failed to search memory" in data["detail"]

    @patch('src.main.assistant.make_decision', side_effect=Exception("Decision error"))
    def test_decision_error_handling(self, mock_make_decision):
        """测试决策错误处理"""
        payload = ["action_1"]
        response = self.client.post("/api/decision", json=payload)
        assert response.status_code == 500
        data = response.json()
        assert "Failed to make decision" in data["detail"]