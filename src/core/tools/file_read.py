"""
File Read Tool — 读取本地文件
"""

from pathlib import Path
from .base import ToolProtocol, ToolResult


class FileReadTool(ToolProtocol):
    name = "read"
    description = "读取文件内容，支持指定行号和范围"
    parameters = {
        "type": "object",
        "properties": {
            "filePath": {"type": "string", "description": "文件绝对路径"},
            "offset": {"type": "integer", "description": "起始行号 (1-indexed)", "default": 1},
            "limit": {"type": "integer", "description": "读取行数", "default": 200},
        },
        "required": ["filePath"],
    }

    async def execute(self, filePath: str, offset: int = 1, limit: int = 200) -> ToolResult:
        path = Path(filePath)
        if not path.exists():
            return ToolResult(output="", error=f"文件不存在: {filePath}")
        if path.is_dir():
            entries = "\n".join(
                f"{'[DIR]' if (path / e).is_dir() else '     '} {e}" for e in sorted(path.iterdir())
            )
            return ToolResult(output=f"目录内容:\n{entries}", metadata={"type": "directory"})

        try:
            lines = path.read_text(encoding="utf-8").splitlines()
            total = len(lines)
            start = max(0, offset - 1)
            end = min(total, start + limit) if limit > 0 else total
            output_lines = [f"{i + 1}: {line}" for i, line in enumerate(lines[start:end], start=start)]

            return ToolResult(
                output="\n".join(output_lines) if output_lines else "(文件为空)",
                metadata={
                    "file": str(path),
                    "total_lines": total,
                    "start_line": start + 1,
                    "end_line": end,
                },
            )
        except UnicodeDecodeError:
            return ToolResult(output="", error=f"无法以 UTF-8 解码: {filePath}")
        except PermissionError:
            return ToolResult(output="", error=f"无权读取: {filePath}")
