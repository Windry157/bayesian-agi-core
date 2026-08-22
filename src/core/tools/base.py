"""
Tool 基础框架
- ToolProtocol: 工具基类
- ToolResult: 工具执行结果
- ToolRegistry: 工具注册中心
- ToolPermission: 权限控制
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ToolPermission(ABC):
    def allow(self, tool_name: str, params: Dict) -> bool:
        return True


@dataclass
class ToolResult:
    output: str = ""
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.error is None

    def to_dict(self) -> Dict:
        return {
            "output": self.output,
            "error": self.error,
            "metadata": self.metadata,
        }


class ToolProtocol(ABC):
    name: str
    description: str
    parameters: Dict[str, Any] = {}

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        ...

    def to_schema(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolProtocol] = {}
        self._permission: Optional[ToolPermission] = None

    def register(self, tool: ToolProtocol):
        self._tools[tool.name] = tool
        logger.info(f"Tool registered: {tool.name}")

    def get(self, name: str) -> Optional[ToolProtocol]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict]:
        return [t.to_schema() for t in self._tools.values()]

    def set_permission(self, permission: ToolPermission):
        self._permission = permission

    async def execute(self, tool_name: str, params: Dict) -> ToolResult:
        tool = self._tools.get(tool_name)
        if tool is None:
            return ToolResult(
                output="",
                error=f"Unknown tool: {tool_name}",
                metadata={"available_tools": list(self._tools.keys())},
            )

        if self._permission and not self._permission.allow(tool_name, params):
            return ToolResult(
                output="",
                error=f"Permission denied for tool: {tool_name}",
            )

        try:
            return await tool.execute(**params)
        except Exception as e:
            logger.error(f"Tool '{tool_name}' failed: {e}")
            return ToolResult(output="", error=str(e))


tool_registry = ToolRegistry()
