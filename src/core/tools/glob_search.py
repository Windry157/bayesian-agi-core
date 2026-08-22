"""
Glob Tool — 文件模式匹配搜索
"""

import os
from pathlib import Path
from typing import List
from .base import ToolProtocol, ToolResult

MAX_RESULTS = 200


class GlobTool(ToolProtocol):
    name = "glob"
    description = "使用 glob 模式匹配文件路径"
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "glob 模式, 如 **/*.py"},
            "path": {"type": "string", "description": "搜索根目录, 默认当前目录"},
        },
        "required": ["pattern"],
    }

    async def execute(self, pattern: str, path: str = ".") -> ToolResult:
        root = Path(path)
        if not root.exists():
            return ToolResult(output="", error=f"目录不存在: {path}")

        matches: List[str] = []
        try:
            for p in root.glob(pattern):
                relative = str(p)
                if p.is_dir():
                    relative += "/"
                matches.append(relative)
                if len(matches) >= MAX_RESULTS:
                    break
        except PermissionError as e:
            return ToolResult(output="", error=f"权限不足: {e}")

        matches.sort()
        if not matches:
            return ToolResult(output="(无匹配)", metadata={"pattern": pattern, "count": 0})

        return ToolResult(
            output="\n".join(matches),
            metadata={"pattern": pattern, "count": len(matches), "truncated": len(matches) >= MAX_RESULTS},
        )
