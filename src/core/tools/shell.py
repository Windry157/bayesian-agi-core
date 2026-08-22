"""
Shell Tool — 执行系统命令
"""

import asyncio
import logging
from .base import ToolProtocol, ToolResult

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 120
MAX_OUTPUT = 50_000


class ShellTool(ToolProtocol):
    name = "shell"
    description = "执行系统命令 (bash/cmd)，返回 stdout + stderr"
    parameters = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "要执行的命令"},
            "workdir": {"type": "string", "description": "工作目录"},
            "timeout": {"type": "integer", "description": "超时毫秒", "default": DEFAULT_TIMEOUT * 1000},
        },
        "required": ["command"],
    }

    async def execute(
        self, command: str, workdir: str = ".", timeout: int = DEFAULT_TIMEOUT * 1000
    ) -> ToolResult:
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workdir,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout / 1000
            )
        except asyncio.TimeoutError:
            return ToolResult(
                output="",
                error=f"命令超时 ({timeout}ms): {command[:80]}",
            )
        except FileNotFoundError:
            return ToolResult(output="", error=f"命令未找到: {command[:80]}")
        except Exception as e:
            return ToolResult(output="", error=str(e))

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr_decoded = stderr_bytes.decode("utf-8", errors="replace")

        if len(stdout) > MAX_OUTPUT:
            stdout = stdout[:MAX_OUTPUT] + f"\n...(截断，共 {len(stdout)} 字节)"
        if len(stderr_decoded) > MAX_OUTPUT:
            stderr_decoded = stderr_decoded[:MAX_OUTPUT] + f"\n...(截断)"

        output = stdout
        if stderr_decoded.strip():
            output += f"\n[stderr]\n{stderr_decoded}"

        return ToolResult(
            output=output or "(无输出)",
            metadata={"exit_code": proc.returncode, "command": command},
        )
