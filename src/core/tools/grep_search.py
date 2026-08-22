"""
Grep Tool — 文件内容正则搜索
"""

import re
from pathlib import Path
from typing import List
from .base import ToolProtocol, ToolResult

MAX_RESULTS = 200


class GrepTool(ToolProtocol):
    name = "grep"
    description = "使用正则表达式搜索文件内容"
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "正则表达式"},
            "path": {"type": "string", "description": "搜索目录, 默认当前目录"},
            "include": {"type": "string", "description": "限定文件模式, 如 *.py"},
        },
        "required": ["pattern"],
    }

    async def execute(self, pattern: str, path: str = ".", include: str = "*") -> ToolResult:
        root = Path(path)
        if not root.exists():
            return ToolResult(output="", error=f"目录不存在: {path}")

        try:
            regex = re.compile(pattern)
        except re.error as e:
            return ToolResult(output="", error=f"无效的正则表达式: {e}")

        results: List[str] = []
        try:
            for file_path in root.glob(f"**/{include}"):
                if file_path.is_dir():
                    continue
                if len(results) >= MAX_RESULTS:
                    break
                try:
                    text = file_path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, PermissionError):
                    continue
                for lineno, line in enumerate(text.splitlines(), 1):
                    if regex.search(line):
                        relative = str(file_path)
                        results.append(f"{relative}:{lineno}: {line}")
                        if len(results) >= MAX_RESULTS:
                            break
        except PermissionError:
            pass

        if not results:
            return ToolResult(output="(无匹配)", metadata={"pattern": pattern, "count": 0})

        return ToolResult(
            output="\n".join(results),
            metadata={"pattern": pattern, "count": len(results), "truncated": len(results) >= MAX_RESULTS},
        )
