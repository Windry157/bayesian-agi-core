#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP Server 集成测试
测试 MCP Server 的所有核心功能
"""

import pytest
import json
import asyncio
from httpx import AsyncClient, ASGITransport
from src.mcp_server import app, BayesianMCPServer


@pytest.fixture
def mcp_server():
    """创建MCP服务器实例"""
    return BayesianMCPServer(host="0.0.0.0", port=8090)


@pytest.fixture
async def async_client():
    """创建异步HTTP客户端"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestHealthEndpoints:
    """健康检查端点测试"""

    @pytest.mark.asyncio
    async def test_root_endpoint(self, async_client):
        """测试根端点"""
        response = await async_client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "BayesianAGICore"
        assert "version" in data
        assert "protocolVersion" in data
        assert "capabilities" in data

    @pytest.mark.asyncio
    async def test_health_endpoint(self, async_client):
        """测试健康检查端点"""
        response = await async_client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["server"] == "BayesianAGICore"

    @pytest.mark.asyncio
    async def test_detailed_health_endpoint(self, async_client):
        """测试详细健康检查端点"""
        response = await async_client.get("/health/detailed")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "checks" in data
        assert "uptime" in data
        assert "metrics" in data


class TestToolsEndpoints:
    """工具端点测试"""

    @pytest.mark.asyncio
    async def test_tools_list(self, async_client):
        """测试工具列表端点"""
        response = await async_client.get("/tools")
        assert response.status_code == 200

        data = response.json()
        assert "tools" in data
        assert len(data["tools"]) >= 8  # 至少8个工具

        # 验证必需的工具存在
        tool_names = [tool["name"] for tool in data["tools"]]
        assert "evaluate_code_confidence" in tool_names
        assert "retrieve_similar_bugs" in tool_names
        assert "predict_complexity" in tool_names
        assert "optimize_memory" in tool_names
        assert "active_inference" in tool_names

    @pytest.mark.asyncio
    async def test_tool_schema(self, async_client):
        """测试工具schema结构"""
        response = await async_client.get("/tools")
        data = response.json()

        for tool in data["tools"]:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert tool["inputSchema"]["type"] == "object"


class TestResourcesEndpoints:
    """资源端点测试"""

    @pytest.mark.asyncio
    async def test_resources_list(self, async_client):
        """测试资源列表端点"""
        response = await async_client.get("/resources")
        assert response.status_code == 200

        data = response.json()
        assert "resources" in data
        assert len(data["resources"]) >= 5  # 至少5个资源

        # 验证必需的资源存在
        resource_uris = [res["uri"] for res in data["resources"]]
        assert "bayesian://memory/snapshot" in resource_uris
        assert "bayesian://metrics/free-energy" in resource_uris
        assert "bayesian://cognition/state" in resource_uris

    @pytest.mark.asyncio
    async def test_resource_schema(self, async_client):
        """测试资源schema结构"""
        response = await async_client.get("/resources")
        data = response.json()

        for resource in data["resources"]:
            assert "uri" in resource
            assert "name" in resource
            assert "description" in resource
            assert "mimeType" in resource


class TestMCProtocol:
    """MCP协议测试"""

    @pytest.mark.asyncio
    async def test_initialize_request(self, async_client):
        """测试初始化请求"""
        request = {
            "jsonrpc": "2.0",
            "id": "test-001",
            "method": "initialize",
            "params": {}
        }

        response = await async_client.post("/mcp", json=request)
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == "test-001"
        assert "result" in data
        assert data["result"]["serverInfo"]["name"] == "BayesianAGICore"

    @pytest.mark.asyncio
    async def test_tools_list_request(self, async_client):
        """测试工具列表请求"""
        request = {
            "jsonrpc": "2.0",
            "id": "test-002",
            "method": "tools/list",
            "params": {}
        }

        response = await async_client.post("/mcp", json=request)
        assert response.status_code == 200

        data = response.json()
        assert "result" in data
        assert "tools" in data["result"]
        assert len(data["result"]["tools"]) >= 8

    @pytest.mark.asyncio
    async def test_tools_call_request(self, async_client):
        """测试工具调用请求"""
        request = {
            "jsonrpc": "2.0",
            "id": "test-003",
            "method": "tools/call",
            "params": {
                "name": "evaluate_code_confidence",
                "arguments": {
                    "code": "def hello(): print('hi')",
                    "language": "python"
                }
            }
        }

        response = await async_client.post("/mcp", json=request)
        assert response.status_code == 200

        data = response.json()
        assert "result" in data
        assert "content" in data["result"]
        assert len(data["result"]["content"]) > 0
        assert data["result"]["content"][0]["type"] == "text"

    @pytest.mark.asyncio
    async def test_resources_list_request(self, async_client):
        """测试资源列表请求"""
        request = {
            "jsonrpc": "2.0",
            "id": "test-004",
            "method": "resources/list",
            "params": {}
        }

        response = await async_client.post("/mcp", json=request)
        assert response.status_code == 200

        data = response.json()
        assert "result" in data
        assert "resources" in data["result"]

    @pytest.mark.asyncio
    async def test_ping_request(self, async_client):
        """测试ping请求"""
        request = {
            "jsonrpc": "2.0",
            "id": "test-005",
            "method": "ping",
            "params": {}
        }

        response = await async_client.post("/mcp", json=request)
        assert response.status_code == 200

        data = response.json()
        assert data["result"]["pong"] == True

    @pytest.mark.asyncio
    async def test_unknown_method(self, async_client):
        """测试未知方法"""
        request = {
            "jsonrpc": "2.0",
            "id": "test-006",
            "method": "unknown/method",
            "params": {}
        }

        response = await async_client.post("/mcp", json=request)
        assert response.status_code == 200

        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32601  # Method not found


class TestBayesianReasoning:
    """贝叶斯推理功能测试"""

    @pytest.mark.asyncio
    async def test_evaluate_code_confidence(self, async_client):
        """测试代码置信度评估"""
        request = {
            "jsonrpc": "2.0",
            "id": "test-007",
            "method": "tools/call",
            "params": {
                "name": "evaluate_code_confidence",
                "arguments": {
                    "code": """
def calculate_sum(a, b):
    return a + b
                    """,
                    "language": "python"
                }
            }
        }

        response = await async_client.post("/mcp", json=request)
        assert response.status_code == 200

        data = response.json()
        result = json.loads(data["result"]["content"][0]["text"])

        assert "confidence_score" in result
        assert "confidence_level" in result
        assert 0 <= result["confidence_score"] <= 1
        assert result["confidence_level"] in ["high", "medium", "low", "very_low"]

    @pytest.mark.asyncio
    async def test_retrieve_similar_bugs(self, async_client):
        """测试相似Bug检索"""
        request = {
            "jsonrpc": "2.0",
            "id": "test-008",
            "method": "tools/call",
            "params": {
                "name": "retrieve_similar_bugs",
                "arguments": {
                    "query": "空指针异常",
                    "limit": 3
                }
            }
        }

        response = await async_client.post("/mcp", json=request)
        assert response.status_code == 200

        data = response.json()
        result = json.loads(data["result"]["content"][0]["text"])

        assert "results" in result
        assert len(result["results"]) <= 3

    @pytest.mark.asyncio
    async def test_predict_complexity(self, async_client):
        """测试代码复杂度预测"""
        request = {
            "jsonrpc": "2.0",
            "id": "test-009",
            "method": "tools/call",
            "params": {
                "name": "predict_complexity",
                "arguments": {
                    "code": "def example(): pass",
                    "language": "python"
                }
            }
        }

        response = await async_client.post("/mcp", json=request)
        assert response.status_code == 200

        data = response.json()
        result = json.loads(data["result"]["content"][0]["text"])

        assert "cyclomatic_complexity" in result
        assert "maintainability_index" in result

    @pytest.mark.asyncio
    async def test_optimize_memory(self, async_client):
        """测试记忆优化"""
        request = {
            "jsonrpc": "2.0",
            "id": "test-010",
            "method": "tools/call",
            "params": {
                "name": "optimize_memory",
                "arguments": {
                    "action": "compact",
                    "target": "all"
                }
            }
        }

        response = await async_client.post("/mcp", json=request)
        assert response.status_code == 200

        data = response.json()
        result = json.loads(data["result"]["content"][0]["text"])

        assert "free_energy_before" in result
        assert "free_energy_after" in result

    @pytest.mark.asyncio
    async def test_active_inference(self, async_client):
        """测试主动推理"""
        request = {
            "jsonrpc": "2.0",
            "id": "test-011",
            "method": "tools/call",
            "params": {
                "name": "active_inference",
                "arguments": {
                    "current_state": "初始状态",
                    "goal_state": "目标状态",
                    "available_actions": ["动作A", "动作B", "动作C"]
                }
            }
        }

        response = await async_client.post("/mcp", json=request)
        assert response.status_code == 200

        data = response.json()
        result = json.loads(data["result"]["content"][0]["text"])

        assert "recommended_action" in result
        assert "action_probabilities" in result

    @pytest.mark.asyncio
    async def test_semantic_search(self, async_client):
        """测试语义搜索"""
        request = {
            "jsonrpc": "2.0",
            "id": "test-012",
            "method": "tools/call",
            "params": {
                "name": "semantic_search",
                "arguments": {
                    "query": "测试查询",
                    "memory_layers": ["medium_term", "long_term"],
                    "limit": 5
                }
            }
        }

        response = await async_client.post("/mcp", json=request)
        assert response.status_code == 200

        data = response.json()
        result = json.loads(data["result"]["content"][0]["text"])

        assert "results" in result
        assert "total_results" in result

    @pytest.mark.asyncio
    async def test_generate_insight(self, async_client):
        """测试洞察生成"""
        request = {
            "jsonrpc": "2.0",
            "id": "test-013",
            "method": "tools/call",
            "params": {
                "name": "generate_insight",
                "arguments": {
                    "topic": "代码质量",
                    "data_sources": ["memory", "bugs"],
                    "depth": "deep"
                }
            }
        }

        response = await async_client.post("/mcp", json=request)
        assert response.status_code == 200

        data = response.json()
        result = json.loads(data["result"]["content"][0]["text"])

        assert "insights" in result
        assert len(result["insights"]) > 0


class TestErrorHandling:
    """错误处理测试"""

    @pytest.mark.asyncio
    async def test_invalid_json(self, async_client):
        """测试无效JSON"""
        response = await async_client.post(
            "/mcp",
            content=b"not valid json",
            headers={"Content-Type": "application/json"}
        )
        # 应该返回错误
        assert response.status_code in [400, 422, 500]

    @pytest.mark.asyncio
    async def test_missing_required_params(self, async_client):
        """测试缺少必需参数时使用默认值"""
        request = {
            "jsonrpc": "2.0",
            "id": "test-014",
            "method": "tools/call",
            "params": {
                "name": "evaluate_code_confidence",
                "arguments": {}  # 缺少必需参数，将使用默认值
            }
        }

        response = await async_client.post("/mcp", json=request)
        assert response.status_code == 200

        data = response.json()
        assert "result" in data
        assert data["result"]["isError"] == False

    @pytest.mark.asyncio
    async def test_unknown_tool(self, async_client):
        """测试未知工具"""
        request = {
            "jsonrpc": "2.0",
            "id": "test-015",
            "method": "tools/call",
            "params": {
                "name": "unknown_tool",
                "arguments": {}
            }
        }

        response = await async_client.post("/mcp", json=request)
        assert response.status_code == 200

        data = response.json()
        assert "error" in data


class TestServerInfo:
    """服务器信息测试"""

    def test_server_info(self, mcp_server):
        """测试服务器信息"""
        info = mcp_server.get_server_info()

        assert info["name"] == "BayesianAGICore"
        assert info["version"] == "2.0.0"
        assert "protocolVersion" in info
        assert "description" in info
        assert "capabilities" in info
        assert "endpoints" in info

    def test_tools_registration(self, mcp_server):
        """测试工具注册"""
        assert len(mcp_server.tools) >= 8
        assert "evaluate_code_confidence" in mcp_server.tools
        assert "retrieve_similar_bugs" in mcp_server.tools
        assert "predict_complexity" in mcp_server.tools

    def test_resources_registration(self, mcp_server):
        """测试资源注册"""
        assert len(mcp_server.resources) >= 5
        assert "bayesian://memory/snapshot" in mcp_server.resources
        assert "bayesian://metrics/free-energy" in mcp_server.resources


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
