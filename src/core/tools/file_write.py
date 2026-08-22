"""
File Write Tool — 写入/创建本地文件
"""

from pathlib import Path
from .base import ToolProtocol, ToolResult


class FileWriteTool(ToolProtocol):
    name = "write"
    description = "写入内容到文件，会覆盖已有文件"
    parameters = {
        "type": "object",
        "properties": {
            "filePath": {"type": "string", "description": "文件绝对路径"},
            "content": {"type": "string", "description": "要写入的内容"},
        },
        "required": ["filePath", "content"],
    }

    async def execute(self, filePath: str, content: str) -> ToolResult:
        path = Path(filePath)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            existed = path.exists()
            path.write_text(content, encoding="utf-8")
            size = path.stat().st_size
            return ToolResult(
                output=f"{'已更新' if existed else '已创建'} {filePath} ({size} 字节)",
                metadata={"file": str(path), "size": size, "created": not existed},
            )
        except PermissionError:
            return ToolResult(output="", error=f"无权写入: {filePath}")
        except OSError as e:
            return ToolResult(output="", error=f"写入失败: {e}")
