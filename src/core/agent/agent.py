#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 框架 - 实现复杂任务规划与执行
基于 ReAct (Reasoning + Acting) 模式
"""

import ast
import operator
import httpx
import json
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

class ActionStatus(Enum):
    """动作执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    WAITING = "waiting"

@dataclass
class Thought:
    """思考记录"""
    step: int
    thought: str
    action: str
    action_input: Dict[str, Any]
    observation: str = ""
    status: ActionStatus = ActionStatus.PENDING

@dataclass
class AgentState:
    """Agent 状态"""
    task: str
    thoughts: List[Thought] = field(default_factory=list)
    current_step: int = 0
    max_steps: int = 10
    context: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    is_complete: bool = False
    final_answer: str = ""

class Tool:
    """工具基类"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    async def execute(self, **kwargs) -> str:
        """执行工具"""
        raise NotImplementedError
    
    def get_schema(self) -> Dict[str, Any]:
        """获取工具的 JSON Schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self._get_parameters()
        }
    
    def _get_parameters(self) -> Dict[str, Any]:
        """获取参数 Schema"""
        return {"type": "object", "properties": {}}


class KnowledgeBaseTool(Tool):
    """知识库检索工具"""
    
    def __init__(self, hybrid_search, rag_retriever):
        super().__init__(
            name="knowledge_search",
            description="在知识库中检索相关信息。适用于查找文档、政策、流程等知识性问题。"
        )
        self.hybrid_search = hybrid_search
        self.rag_retriever = rag_retriever
    
    async def execute(self, query: str, top_k: int = 5) -> str:
        results = await self.hybrid_search.hybrid_search(query, top_k=top_k)
        
        if not results:
            return "未找到相关信息。"
        
        response = "找到以下相关信息：\n\n"
        for i, r in enumerate(results, 1):
            response += f"[{i}] {r['source']} (相关度: {r['combined_score']:.2f})\n"
            response += f"内容: {r['content'][:300]}...\n\n"
        
        return response


class CodeAnalysisTool(Tool):
    """代码分析工具"""
    
    def __init__(self, code_analyzer):
        super().__init__(
            name="code_analyze",
            description="分析代码的复杂度、错误和性能问题。适用于代码审查和优化建议。"
        )
        self.code_analyzer = code_analyzer
    
    async def execute(self, code: str, analysis_type: str = "full") -> str:
        if analysis_type == "complexity":
            result = self.code_analyzer.analyze_complexity(code)
        elif analysis_type == "errors":
            errors = self.code_analyzer.detect_errors(code)
            result = {"success": True, "data": {"errors": errors}}
        else:
            complexity = self.code_analyzer.analyze_complexity(code)
            errors = self.code_analyzer.detect_errors(code)
            result = {"success": True, "data": {"complexity": complexity, "errors": errors}}
        
        if not result.get("success"):
            return f"分析失败: {result.get('error')}"
        
        response = "代码分析结果：\n\n"
        
        if "complexity" in result["data"]:
            c = result["data"]["complexity"]
            response += f"- 代码行数: {c.get('loc', 0)}\n"
            response += f"- 函数数量: {c.get('functions', 0)}\n"
            response += f"- 类数量: {c.get('classes', 0)}\n"
            response += f"- 圈复杂度: {c.get('cyclomatic_complexity', 0)}\n"
        
        if "errors" in result["data"]:
            errors = result["data"]["errors"]
            if errors:
                response += "\n检测到的问题：\n"
                for e in errors[:5]:
                    response += f"- [行 {e.get('line', '?')}] {e.get('message', '')}\n"
            else:
                response += "\n未检测到语法错误。\n"
        
        return response


class MemoryTool(Tool):
    """记忆系统工具"""
    
    def __init__(self, memory_system):
        super().__init__(
            name="memory_search",
            description="搜索记忆系统中的相关信息。适用于查找历史对话、项目经验等。"
        )
        self.memory_system = memory_system
    
    async def execute(self, query: str, top_k: int = 5) -> str:
        results = await self.memory_system.retrieve_memories(query, top_k=top_k)
        
        if not results:
            return "未找到相关记忆。"
        
        response = "找到以下相关记忆：\n\n"
        for i, r in enumerate(results, 1):
            content = r.get("content", "")[:200]
            response += f"[{i}] {content}...\n\n"
        
        return response


class CalculatorTool(Tool):
    """计算器工具"""
    
    def __init__(self):
        super().__init__(
            name="calculate",
            description="执行数学计算。适用于数据分析、统计分析等需要计算的任务。"
        )
    
    async def execute(self, expression: str) -> str:
        try:
            result = _safe_eval(expression)
            return f"计算结果: {result}"
        except Exception as e:
            return f"计算错误: {str(e)}"

def _safe_eval(expr: str) -> float:
    _allowed_ops = {
        ast.Add: operator.add, ast.Sub: operator.sub,
        ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
        ast.Pow: operator.pow, ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }
    _allowed_nodes = (ast.Expression, ast.Constant, ast.UnaryOp, ast.BinOp)

    node = ast.parse(expr.strip(), mode="eval")
    def _eval(n):
        if isinstance(n, ast.Constant):
            if not isinstance(n.value, (int, float)):
                raise ValueError(f"unsupported constant: {n.value}")
            return n.value
        if isinstance(n, ast.UnaryOp):
            if type(n.op) not in _allowed_ops:
                raise ValueError(f"unsupported operator: {type(n.op).__name__}")
            return _allowed_ops[type(n.op)](_eval(n.operand))
        if isinstance(n, ast.BinOp):
            if type(n.op) not in _allowed_ops:
                raise ValueError(f"unsupported operator: {type(n.op).__name__}")
            return _allowed_ops[type(n.op)](_eval(n.left), _eval(n.right))
        raise ValueError(f"unsupported expression: {type(n).__name__}")
    return _eval(node.body)


class WebSearchTool(Tool):
    """网络搜索工具"""
    
    def __init__(self, ollama_url: str = "http://192.168.3.105:11434"):
        super().__init__(
            name="web_search",
            description="搜索网络获取最新信息。适用于查找实时数据、新闻等。"
        )
        self.ollama_url = ollama_url
    
    async def execute(self, query: str) -> str:
        prompt = f"""
请为以下查询生成一个搜索策略：

查询：{query}

请列出3-5个相关的搜索关键词，这些关键词应该能帮助找到最新、最相关的信息。
"""
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": "llama3.1:8b",
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False
                    }
                )
                data = response.json()
                return data.get("message", {}).get("content", "无法生成搜索建议")
        except Exception as e:
            return f"搜索失败: {str(e)}"


class Agent:
    """Agent 核心类 - 基于 ReAct 模式"""
    
    def __init__(
        self,
        ollama_url: str = "http://192.168.3.105:11434",
        model: str = "llama3.1:8b"
    ):
        self.ollama_url = ollama_url
        self.model = model
        self.tools: Dict[str, Tool] = {}
        self.state: Optional[AgentState] = None
    
    def register_tool(self, tool: Tool):
        """注册工具"""
        self.tools[tool.name] = tool
    
    def get_tools_description(self) -> str:
        """获取所有工具的描述"""
        if not self.tools:
            return "无可用工具。"
        
        description = "可用工具：\n"
        for name, tool in self.tools.items():
            description += f"\n{tool.name}: {tool.description}\n"
        
        return description
    
    async def think(self, prompt: str) -> str:
        """调用 LLM 进行思考"""
        tools_desc = self.get_tools_description()
        
        context = ""
        if self.state and self.state.thoughts:
            context = "\n\n之前的推理步骤：\n"
            for t in self.state.thoughts[-5:]:
                context += f"\n步骤 {t.step}:\n"
                context += f"思考: {t.thought}\n"
                context += f"动作: {t.action}\n"
                context += f"结果: {t.observation}\n"
        
        system_prompt = f"""你是一个智能助手，能够分解复杂任务并使用工具来解决问题。

{tools_desc}

{context}

当前任务：{prompt}

请按照以下格式进行推理：

思考: 分析当前情况，决定下一步应该做什么
动作: 选择一个工具并说明参数（如果没有合适的工具，可以回答"完成"）
动作输入: {{"参数名": "参数值"}}
"""
        
        if hasattr(self, '_llm') and self._llm is not None:
            try:
                from ..llm.base_llm import Message
                msgs = [Message(role="user", content=system_prompt)]
                resp = await self._llm.chat(msgs)
                return resp.content
            except Exception as e:
                return f"思考失败(LM): {str(e)}"
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": system_prompt}],
                        "stream": False
                    }
                )
                response.raise_for_status()
                data = response.json()
                return data.get("message", {}).get("content", "")
        except Exception as e:
            return f"思考失败: {str(e)}"

    def set_llm(self, llm):
        """设置 LLM 实例（用于通过 LLMRouter 调用）"""
        self._llm = llm
    
    def parse_thought(self, thought_text: str) -> Dict[str, Any]:
        """解析思考结果"""
        result = {
            "thought": "",
            "action": None,
            "action_input": {}
        }
        
        lines = thought_text.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("思考:"):
                result["thought"] = line[3:].strip()
            elif line.startswith("动作:"):
                action = line[3:].strip().lower()
                if "完成" in action or "结束" in action or "没有" in action:
                    result["action"] = "finish"
                elif "knowledge" in action:
                    result["action"] = "knowledge_search"
                elif "code" in action:
                    result["action"] = "code_analyze"
                elif "memory" in action:
                    result["action"] = "memory_search"
                elif "calculate" in action:
                    result["action"] = "calculate"
                elif "search" in action or "web" in action:
                    result["action"] = "web_search"
            elif line.startswith("动作输入:") or line.startswith("参数"):
                try:
                    json_str = line.split(":", 1)[1].strip()
                    if json_str.startswith("{"):
                        result["action_input"] = json.loads(json_str)
                except:
                    pass
        
        return result
    
    async def execute_action(self, action: str, action_input: Dict[str, Any]) -> str:
        """执行动作"""
        if action == "finish":
            return "TASK_COMPLETE"
        
        if action not in self.tools:
            return f"工具 '{action}' 不存在。"
        
        try:
            tool = self.tools[action]
            result = await tool.execute(**action_input)
            return result
        except Exception as e:
            return f"执行失败: {str(e)}"
    
    async def run(self, task: str, max_steps: int = 10) -> AgentState:
        """运行 Agent"""
        self.state = AgentState(
            task=task,
            max_steps=max_steps
        )
        
        for step in range(max_steps):
            self.state.current_step = step + 1
            
            thought_text = await self.think(task)
            
            parsed = self.parse_thought(thought_text)
            
            action = parsed.get("action", "finish")
            action_input = parsed.get("action_input", {})
            
            thought = Thought(
                step=self.state.current_step,
                thought=parsed.get("thought", ""),
                action=action,
                action_input=action_input
            )
            
            observation = await self.execute_action(action, action_input)
            thought.observation = observation
            thought.status = ActionStatus.SUCCESS if action == "finish" else ActionStatus.COMPLETED
            
            self.state.thoughts.append(thought)
            self.state.history.append({
                "step": self.state.current_step,
                "thought": thought.thought,
                "action": action,
                "observation": observation
            })
            
            if action == "finish":
                self.state.is_complete = True
                self.state.final_answer = observation
                break
        
        if not self.state.is_complete:
            self.state.final_answer = f"任务在 {max_steps} 步后仍未完成。"
        
        return self.state
    
    def get_trace(self) -> List[Dict[str, Any]]:
        """获取推理轨迹"""
        if not self.state:
            return []
        
        return [
            {
                "step": t.step,
                "thought": t.thought,
                "action": t.action,
                "action_input": t.action_input,
                "observation": t.observation,
                "status": t.status.value
            }
            for t in self.state.thoughts
        ]


class SimpleAgent:
    """简化版 Agent - 直接基于工具调用"""
    
    def __init__(self, ollama_url: str = "http://192.168.3.105:11434"):
        self.ollama_url = ollama_url
        self.tools: Dict[str, Tool] = {}
    
    def register_tool(self, tool: Tool):
        self.tools[tool.name] = tool
    
    async def plan_and_execute(self, task: str) -> Dict[str, Any]:
        """规划并执行任务"""
        tools_json = json.dumps([t.get_schema() for t in self.tools.values()], ensure_ascii=False, indent=2)
        
        plan_prompt = f"""
你是一个任务规划专家。请将以下任务分解为具体的执行步骤，并为每个步骤选择合适的工具。

可用工具：
{tools_json}

任务：{task}

请按以下 JSON 格式输出执行计划：
```json
{{
  "steps": [
    {{
      "step": 1,
      "description": "步骤描述",
      "tool": "工具名称",
      "parameters": {{"参数": "值"}}
    }}
  ],
  "final_answer_format": "最终答案的格式要求"
}}
```
"""
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": "llama3.1:8b",
                        "messages": [{"role": "user", "content": plan_prompt}],
                        "stream": False
                    }
                )
                response.raise_for_status()
                data = response.json()
                plan_text = data.get("message", {}).get("content", "")
                
                import re
                json_match = re.search(r'\{.*\}', plan_text, re.DOTALL)
                if json_match:
                    plan = json.loads(json_match.group())
                else:
                    plan = {"steps": [], "final_answer_format": "text"}
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "steps": [],
                "results": []
            }
        
        results = []
        for step in plan.get("steps", []):
            tool_name = step.get("tool")
            parameters = step.get("parameters", {})
            
            if tool_name in self.tools:
                try:
                    result = await self.tools[tool_name].execute(**parameters)
                    results.append({
                        "step": step.get("step"),
                        "description": step.get("description"),
                        "tool": tool_name,
                        "result": result,
                        "success": True
                    })
                except Exception as e:
                    results.append({
                        "step": step.get("step"),
                        "description": step.get("description"),
                        "tool": tool_name,
                        "result": f"执行失败: {str(e)}",
                        "success": False
                    })
            else:
                results.append({
                    "step": step.get("step"),
                    "description": step.get("description"),
                    "tool": tool_name,
                    "result": f"工具不存在: {tool_name}",
                    "success": False
                })
        
        return {
            "success": True,
            "task": task,
            "plan": plan,
            "steps": plan.get("steps", []),
            "results": results,
            "final_answer_format": plan.get("final_answer_format", "text")
        }
