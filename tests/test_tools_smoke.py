"""
Coding Tools 验证 - Pytest 版本
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.core.tools import register_all, tool_registry

pytestmark = pytest.mark.asyncio


class TestTools:
    async def test_list_tools(self):
        register_all()
        tools = tool_registry.list_tools()
        assert len(tools) >= 6

    async def test_read_tool(self):
        register_all()
        result = await tool_registry.execute("read", {"filePath": __file__, "limit": 5})
        assert result.success
        assert "Coding Tools" in result.output

    async def test_write_and_edit_tool(self, tmp_path):
        register_all()
        tmp = tmp_path / "test_tool_tmp.txt"
        result = await tool_registry.execute("write", {"filePath": str(tmp), "content": "hello tools"})
        assert result.success
        result = await tool_registry.execute("edit", {"filePath": str(tmp), "oldString": "hello tools", "newString": "hello world"})
        assert result.success
        result = await tool_registry.execute("read", {"filePath": str(tmp)})
        assert "hello world" in result.output

    async def test_unknown_tool(self):
        register_all()
        result = await tool_registry.execute("nonexistent", {})
        assert not result.success
        assert "Unknown tool" in result.error
