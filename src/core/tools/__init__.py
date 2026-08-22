"""
Coding Tools — OpenClaw 兼容工具系统

提供文件读写、shell 执行、代码搜索等编码工具。
"""

from .base import ToolProtocol, ToolResult, ToolRegistry, tool_registry, ToolPermission
from .file_read import FileReadTool
from .file_write import FileWriteTool
from .file_edit import FileEditTool
from .shell import ShellTool
from .glob_search import GlobTool
from .grep_search import GrepTool
from .reason import ReasonTool

__all__ = [
    "ToolProtocol",
    "ToolResult",
    "ToolRegistry",
    "tool_registry",
    "ToolPermission",
    "FileReadTool",
    "FileWriteTool",
    "FileEditTool",
    "ShellTool",
    "GlobTool",
    "GrepTool",
    "ReasonTool",
]


def register_all():
    tool_registry.register(FileReadTool())
    tool_registry.register(FileWriteTool())
    tool_registry.register(FileEditTool())
    tool_registry.register(ShellTool())
    tool_registry.register(GlobTool())
    tool_registry.register(GrepTool())
    tool_registry.register(ReasonTool())
