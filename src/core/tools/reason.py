"""
Reason Tool — 基于 LLM 的分析推理

让贝叶斯大脑具备真正的"决策分析"能力，而不只是执行文件/命令工具。
输入待分析的数据/问题，模型基于数据给出推理结论与建议。

继承 OpenClaw 兼容的 ToolProtocol。
"""

import logging
from typing import Any, Dict, Optional

from .base import ToolProtocol, ToolResult

logger = logging.getLogger(__name__)


class ReasonTool(ToolProtocol):
    name = "reason"
    description = "对给定数据/问题进行 LLM 分析推理，输出结构化结论与建议"
    parameters = {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "要分析推理的问题"},
            "data": {"type": "string", "description": "待分析的数据/上下文"},
            "model": {"type": "string", "description": "使用的模型名，默认 gemma4:12b"},
        },
        "required": ["question"],
    }

    def __init__(self, ollama_url: str = "http://192.168.3.105:11434",
                 default_model: str = "gemma4:12b"):
        self.ollama_url = ollama_url
        self.default_model = default_model

    async def execute(
        self,
        question: str,
        data: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> ToolResult:
        """执行 LLM 推理（直接用 Ollama，超时充分）。"""
        import httpx
        model = model or self.default_model
        prompt = (
            "你是一个严谨的分析推理引擎。请基于提供的数据，对问题进行分析，"
            "输出：\n1. 核心结论\n2. 关键依据\n3. 建议/下一步\n"
            f"\n问题：{question}\n"
        )
        if data:
            prompt += f"\n数据：{data}\n"

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                raw = await client.post(
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                        "options": {
                            "num_predict": 600,
                            "temperature": 0.4,
                            "top_p": 0.9,
                        },
                    },
                )
                raw.raise_for_status()
                data_json = raw.json()
                text = data_json.get("message", {}).get("content", "")
                if not text:
                    text = data_json.get("message", {}).get("thinking", "") or "(无输出)"
                return ToolResult(
                    output=text,
                    metadata={"model": model, "tool": "reason"},
                )
        except Exception as e:
            logger.error(f"reason 工具失败: {e}")
            return ToolResult(output="", error=f"推理失败: {e}")
