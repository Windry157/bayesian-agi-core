"""
File Edit Tool — 字符串替换编辑文件
"""

from pathlib import Path
from .base import ToolProtocol, ToolResult


class FileEditTool(ToolProtocol):
    name = "edit"
    description = "在文件中进行精确字符串替换"
    parameters = {
        "type": "object",
        "properties": {
            "filePath": {"type": "string", "description": "文件绝对路径"},
            "oldString": {"type": "string", "description": "要替换的旧字符串"},
            "newString": {"type": "string", "description": "替换后的新字符串"},
            "replaceAll": {"type": "boolean", "description": "替换所有匹配", "default": False},
        },
        "required": ["filePath", "oldString", "newString"],
    }

    async def execute(
        self, filePath: str, oldString: str, newString: str, replaceAll: bool = False
    ) -> ToolResult:
        path = Path(filePath)
        if not path.exists():
            return ToolResult(output="", error=f"文件不存在: {filePath}")

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return ToolResult(output="", error=f"无法以 UTF-8 解码: {filePath}")

        count = content.count(oldString)
        if count == 0:
            return ToolResult(output="", error=f"未找到匹配内容: {oldString[:60]}...")

        if not replaceAll and count > 1:
            return ToolResult(
                output="",
                error=f"找到 {count} 处匹配，请扩大匹配范围或使用 replaceAll=true",
                metadata={"matches": count},
            )

        new_content = content.replace(oldString, newString) if replaceAll else content.replace(oldString, newString, 1)
        actual_count = 1 if not replaceAll else count

        try:
            path.write_text(new_content, encoding="utf-8")
            return ToolResult(
                output=f"已替换 {actual_count} 处 in {filePath}",
                metadata={"file": str(path), "replacements": actual_count},
            )
        except PermissionError:
            return ToolResult(output="", error=f"无权写入: {filePath}")
