import pytest
from dataclasses import asdict
from src.mcp.protocol import MCPMessage, MCPRequest, MCPResponse, ToolDefinition, ResourceDefinition


class TestMCPMessage:
    def test_default_values(self):
        msg = MCPMessage()
        assert msg.jsonrpc == "2.0"
        assert msg.id is None

    def test_custom_values(self):
        msg = MCPMessage(id="test-1")
        assert msg.id == "test-1"


class TestMCPRequest:
    def test_default_method(self):
        req = MCPRequest()
        assert req.method == ""
        assert req.params is None

    def test_with_params(self):
        req = MCPRequest(method="ping", params={"key": "value"})
        assert req.method == "ping"
        assert req.params == {"key": "value"}


class TestMCPResponse:
    def test_success_response(self):
        resp = MCPResponse(id="1", result={"status": "ok"})
        assert resp.id == "1"
        assert resp.result == {"status": "ok"}
        assert resp.error is None

    def test_error_response(self):
        resp = MCPResponse(id="1", error={"code": -32601, "message": "not found"})
        assert resp.error["code"] == -32601


class TestToolDefinition:
    def test_minimal(self):
        tool = ToolDefinition(name="test", description="a test tool", input_schema={"type": "object"})
        assert tool.name == "test"
        assert tool.output_schema is None

    def test_with_output(self):
        tool = ToolDefinition(name="test", description="desc", input_schema={}, output_schema={"type": "string"})
        assert tool.output_schema == {"type": "string"}


class TestResourceDefinition:
    def test_default_mime(self):
        res = ResourceDefinition(uri="test://uri", name="test", description="desc")
        assert res.mime_type == "application/json"

    def test_custom_mime(self):
        res = ResourceDefinition(uri="test://uri", name="test", description="desc", mime_type="text/plain")
        assert res.mime_type == "text/plain"
