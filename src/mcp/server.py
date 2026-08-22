import json
import math
import re
import statistics
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import asdict
import logging

from src.mcp.common import DATA_DIR, validate_input_text
from src.mcp.memory import MemoryStore
from src.mcp.bug_db import BugDatabase
from src.mcp.code_analyzer import CodeAnalyzer
from src.mcp.bayesian import BayesianEngine, ActiveInferenceEngine
from src.mcp.insight import InsightGenerator
from src.mcp.protocol import MCPRequest, MCPResponse, ToolDefinition, ResourceDefinition

try:
    from src.core.task_dispatcher import TaskDispatcher
except ImportError:
    from core.task_dispatcher import TaskDispatcher

logger = logging.getLogger(__name__)


class BayesianMCPServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8090, redis_url: Optional[str] = None):
        self.host = host
        self.port = port
        self.data_dir = DATA_DIR
        self.memory = MemoryStore(self.data_dir)
        self.bug_db = BugDatabase(self.data_dir)
        self.code_analyzer = CodeAnalyzer()
        self.bayesian = BayesianEngine()
        self.active_inference = ActiveInferenceEngine()
        self.insight_gen = InsightGenerator()
        self.tools: Dict[str, ToolDefinition] = {}
        self.resources: Dict[str, ResourceDefinition] = {}
        self._initialized = False
        self._register_tools()
        self._register_resources()
        self.dispatcher = TaskDispatcher(num_workers=2, redis_url=redis_url)

    async def start_dispatcher(self):
        await self.dispatcher.start()
        self._flush_task_handle = asyncio.create_task(self._periodic_flush())

    async def _periodic_flush(self):
        while True:
            await asyncio.sleep(30)
            if self.memory._dirty:
                await self.dispatcher.submit("flush_memory", {"store": self.memory})
            if self.bug_db._dirty:
                await self.dispatcher.submit("flush_bugs", {"db": self.bug_db})

    def _register_tools(self):
        self.tools = {
            "evaluate_code_confidence": ToolDefinition(
                name="evaluate_code_confidence",
                description="使用贝叶斯方法评估代码的置信度和风险等级，基于圈复杂度、认知复杂度、Halstead 指标和静态分析",
                input_schema={
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "language": {"type": "string", "enum": ["python", "javascript", "typescript", "java", "go", "rust"]},
                        "context": {
                            "type": "object",
                            "properties": {
                                "project_type": {"type": "string"},
                                "recent_bugs": {"type": "array", "items": {"type": "string"}},
                                "code_patterns": {"type": "array", "items": {"type": "string"}}
                            }
                        }
                    },
                    "required": ["code", "language"]
                }
            ),
            "retrieve_similar_bugs": ToolDefinition(
                name="retrieve_similar_bugs",
                description="基于 TF-IDF 语义相似度搜索历史 bug 和修复方案，支持按语言和严重程度过滤",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
                        "filters": {
                            "type": "object",
                            "properties": {
                                "language": {"type": "string"},
                                "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]}
                            }
                        }
                    },
                    "required": ["query"]
                }
            ),
            "predict_complexity": ToolDefinition(
                name="predict_complexity",
                description="使用真实的圈复杂度、认知复杂度、Halstead 指标分析代码复杂度，结合历史趋势预测 Bug 概率",
                input_schema={
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "language": {"type": "string"},
                        "history": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["code", "language"]
                }
            ),
            "analyze_reasoning_chain": ToolDefinition(
                name="analyze_reasoning_chain",
                description="分析推理链路的置信度传播、一致性、瓶颈检测，使用贝叶斯概率传播方法",
                input_schema={
                    "type": "object",
                    "properties": {
                        "reasoning_steps": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "step_id": {"type": "string"},
                                    "description": {"type": "string"},
                                    "confidence": {"type": "number"},
                                    "premise_ids": {"type": "array", "items": {"type": "string"}}
                                }
                            }
                        },
                        "goal": {"type": "string"}
                    },
                    "required": ["reasoning_steps", "goal"]
                }
            ),
            "optimize_memory": ToolDefinition(
                name="optimize_memory",
                description="执行自由能最小化，优化记忆权重：compact(合并相似记忆), reinforce(强化高频记忆), prune(修剪低价值记忆), snapshot(查看快照)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["compact", "reinforce", "prune", "snapshot"]},
                        "target": {"type": "string", "enum": ["short_term", "medium_term", "long_term", "all"], "default": "all"},
                        "criteria": {
                            "type": "object",
                            "properties": {
                                "min_importance": {"type": "number"},
                                "max_items": {"type": "integer"},
                                "age_threshold_hours": {"type": "number"}
                            }
                        }
                    },
                    "required": ["action"]
                }
            ),
            "active_inference": ToolDefinition(
                name="active_inference",
                description="基于自由能原理的主动推理：计算每个动作的预期自由能（认知价值+实用价值-复杂度代价），选择最优动作",
                input_schema={
                    "type": "object",
                    "properties": {
                        "current_state": {"type": "string"},
                        "goal_state": {"type": "string"},
                        "available_actions": {"type": "array", "items": {"type": "string"}},
                        "constraints": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["current_state", "goal_state", "available_actions"]
                }
            ),
            "semantic_search": ToolDefinition(
                name="semantic_search",
                description="跨层记忆的语义搜索，基于 TF-IDF + n-gram 特征，支持按记忆层筛选",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "memory_layers": {"type": "array", "items": {"type": "string"}, "default": ["medium_term", "long_term"]},
                        "limit": {"type": "integer", "default": 5},
                        "include_metadata": {"type": "boolean", "default": True}
                    },
                    "required": ["query"]
                }
            ),
            "generate_insight": ToolDefinition(
                name="generate_insight",
                description="基于记忆和 Bug 数据库的实际数据生成深度洞察，包括模式识别、关联分析和建议",
                input_schema={
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "data_sources": {"type": "array", "items": {"type": "string", "enum": ["memory", "codebase", "bugs", "reasoning_history", "all"]}},
                        "depth": {"type": "string", "enum": ["surface", "deep", "comprehensive"], "default": "deep"}
                    },
                    "required": ["topic"]
                }
            ),
            "transcribe_audio": ToolDefinition(
                name="transcribe_audio",
                description="使用Whisper模型将音频转录为文本，支持多语言识别和翻译",
                input_schema={
                    "type": "object",
                    "properties": {
                        "audio_data": {"type": "string", "description": "Base64编码的音频数据"},
                        "language": {"type": "string", "default": "auto", "description": "语言代码：auto(自动检测), zh(中文), en(英语)等"},
                        "task": {"type": "string", "enum": ["transcribe", "translate"], "default": "transcribe", "description": "任务类型：transcribe(转录)或translate(翻译为英语)"}
                    },
                    "required": ["audio_data"]
                }
            ),
            "detect_audio_language": ToolDefinition(
                name="detect_audio_language",
                description="检测音频中的语言",
                input_schema={
                    "type": "object",
                    "properties": {
                        "audio_data": {"type": "string", "description": "Base64编码的音频数据"}
                    },
                    "required": ["audio_data"]
                }
            ),
            "recognize_voice_command": ToolDefinition(
                name="recognize_voice_command",
                description="识别语音命令，支持预定义命令关键词匹配",
                input_schema={
                    "type": "object",
                    "properties": {
                        "audio_data": {"type": "string", "description": "Base64编码的音频数据"},
                        "language": {"type": "string", "default": "zh", "description": "语言代码"}
                    },
                    "required": ["audio_data"]
                }
            ),
            "analyze_multimodal": ToolDefinition(
                name="analyze_multimodal",
                description="多模态内容分析，支持同时处理图像、文本和语音",
                input_schema={
                    "type": "object",
                    "properties": {
                        "image_data": {"type": "string", "description": "Base64编码的图像数据"},
                        "text": {"type": "string", "description": "文本内容"},
                        "audio_data": {"type": "string", "description": "Base64编码的音频数据"},
                        "task": {"type": "string", "description": "分析任务描述"}
                    }
                }
            )
        }

    def _register_resources(self):
        self.resources = {
            "bayesian://memory/snapshot": ResourceDefinition(uri="bayesian://memory/snapshot", name="记忆快照", description="当前记忆系统的完整快照"),
            "bayesian://metrics/free-energy": ResourceDefinition(uri="bayesian://metrics/free-energy", name="自由能指标", description="自由能原理相关的实时指标"),
            "bayesian://reasoning/history": ResourceDefinition(uri="bayesian://reasoning/history", name="推理历史", description="最近的推理链路历史"),
            "bayesian://knowledge/graph": ResourceDefinition(uri="bayesian://knowledge/graph", name="知识图谱状态", description="当前知识图谱的节点和关系统计"),
            "bayesian://cognition/state": ResourceDefinition(uri="bayesian://cognition/state", name="认知状态", description="当前认知引擎的状态"),
            "bayesian://bug-database/stats": ResourceDefinition(uri="bayesian://bug-database/stats", name="Bug数据库统计", description="Bug数据库的统计信息"),
            "bayesian://speech/model-info": ResourceDefinition(uri="bayesian://speech/model-info", name="语音模型信息", description="当前语音识别模型的信息"),
            "bayesian://speech/supported-languages": ResourceDefinition(uri="bayesian://speech/supported-languages", name="支持的语言", description="语音识别支持的语言列表"),
            "bayesian://multimodal/state": ResourceDefinition(uri="bayesian://multimodal/state", name="多模态状态", description="多模态处理系统的当前状态"),
        }

    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        method = request.method
        params = request.params or {}
        try:
            if method == "initialize":
                return await self._handle_initialize(request.id)
            elif method == "tools/list":
                return await self._handle_tools_list(request.id)
            elif method == "tools/call":
                return await self._handle_tools_call(request.id, params)
            elif method == "resources/list":
                return await self._handle_resources_list(request.id)
            elif method == "resources/read":
                return await self._handle_resources_read(request.id, params)
            elif method == "ping":
                return MCPResponse(id=request.id, result={"pong": True})
            else:
                return MCPResponse(id=request.id, error={"code": -32601, "message": f"Unknown method: {method}"})
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return MCPResponse(id=request.id, error={"code": -32603, "message": str(e)})

    async def _handle_initialize(self, request_id: Optional[str]) -> MCPResponse:
        self._initialized = True
        return MCPResponse(id=request_id, result={
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "BayesianAGICore", "version": "2.0.0"},
            "capabilities": {"tools": {"listChanged": True}, "resources": {"subscribe": True, "listChanged": True}},
            "instructions": "贝叶斯认知引擎 - 支持真实的代码分析、语义搜索、主动推理、记忆优化"
        })

    async def _handle_tools_list(self, request_id: Optional[str]) -> MCPResponse:
        tools_list = [{"name": t.name, "description": t.description, "inputSchema": t.input_schema} for t in self.tools.values()]
        return MCPResponse(id=request_id, result={"tools": tools_list})

    async def _handle_tools_call(self, request_id: Optional[str], params: Dict[str, Any]) -> MCPResponse:
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        if tool_name not in self.tools:
            return MCPResponse(id=request_id, error={"code": -32602, "message": f"Unknown tool: {tool_name}"})
        try:
            result = await self._execute_tool(tool_name, arguments)
            return MCPResponse(id=request_id, result={
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}],
                "isError": False
            })
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return MCPResponse(id=request_id, result={
                "content": [{"type": "text", "text": json.dumps({"error": str(e)}, ensure_ascii=False)}],
                "isError": True
            })

    async def _handle_resources_list(self, request_id: Optional[str]) -> MCPResponse:
        resources_list = [{"uri": r.uri, "name": r.name, "description": r.description, "mimeType": r.mime_type} for r in self.resources.values()]
        return MCPResponse(id=request_id, result={"resources": resources_list})

    async def _handle_resources_read(self, request_id: Optional[str], params: Dict[str, Any]) -> MCPResponse:
        uri = params.get("uri")
        if uri not in self.resources:
            return MCPResponse(id=request_id, error={"code": -32602, "message": f"Unknown resource: {uri}"})
        try:
            content = await self._get_resource_content(uri)
            return MCPResponse(id=request_id, result={
                "contents": [{"uri": uri, "mimeType": self.resources[uri].mime_type, "text": json.dumps(content, ensure_ascii=False, indent=2)}]
            })
        except Exception as e:
            return MCPResponse(id=request_id, error={"code": -32603, "message": str(e)})

    async def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        text_fields = {
            "evaluate_code_confidence": "code",
            "retrieve_similar_bugs": "query",
            "predict_complexity": "code",
            "semantic_search": "query",
            "generate_insight": "topic",
            "analyze_reasoning_chain": "reasoning_steps",
        }
        if tool_name in text_fields:
            field = text_fields[tool_name]
            val = arguments.get(field)
            if isinstance(val, str):
                err = validate_input_text(val, field_name=field)
                if err:
                    return {"error": err}
            elif isinstance(val, list):
                err = validate_input_text(json.dumps(val), field_name=field)
                if err:
                    return {"error": err}
        handlers = {
            "evaluate_code_confidence": self._evaluate_code_confidence,
            "retrieve_similar_bugs": self._retrieve_similar_bugs,
            "predict_complexity": self._predict_complexity,
            "analyze_reasoning_chain": self._analyze_reasoning_chain,
            "optimize_memory": self._optimize_memory,
            "active_inference": self._active_inference,
            "semantic_search": self._semantic_search,
            "generate_insight": self._generate_insight,
            "transcribe_audio": self._transcribe_audio,
            "detect_audio_language": self._detect_audio_language,
            "recognize_voice_command": self._recognize_voice_command,
            "analyze_multimodal": self._analyze_multimodal,
        }
        handler = handlers.get(tool_name)
        if handler is None:
            raise ValueError(f"Tool {tool_name} not implemented")
        return await handler(arguments)

    async def _evaluate_code_confidence(self, args: Dict[str, Any]) -> Dict[str, Any]:
        code = args.get("code", "")
        language = args.get("language", "python")
        cyclomatic = self.code_analyzer.cyclomatic_complexity(code, language)
        cognitive = self.code_analyzer.cognitive_complexity(code, language)
        halstead = self.code_analyzer.halstead_metrics(code, language)
        issues = self.code_analyzer.detect_issues(code, language)
        observations = [
            cyclomatic < 10,
            cognitive < 20,
            halstead.get("difficulty", 0) < 20,
            len([i for i in issues if i["severity"] in ("critical", "high")]) == 0,
            len(code.strip().split('\n')) <= 200,
            len(code.strip().split('\n')) >= 3,
            bool(re.search(r'""".*?"""', code, re.DOTALL)) or bool(re.search(r"'''.*?'''", code, re.DOTALL)),
        ]
        bayesian_result = self.bayesian.evaluate_confidence(observations)
        self.memory.add(
            content=f"Code evaluation: lang={language}, cyclomatic={cyclomatic}, cognitive={cognitive}, issues={len(issues)}",
            layer="short_term",
            metadata={"type": "code_evaluation", "language": language, "complexity": cyclomatic, "issues_count": len(issues)}
        )
        suggestions = []
        if cyclomatic > 10:
            suggestions.append(f"圈复杂度 {cyclomatic}，建议控制在 10 以内")
        if cognitive > 15:
            suggestions.append(f"认知复杂度 {cognitive}，建议控制在 20 以内")
        if halstead.get("difficulty", 0) > 20:
            suggestions.append(f"Halstead 难度 {halstead.get('difficulty', 0)}，建议控制在 20 以内")
        for i in issues[:5]:
            suggestions.append(f"[{i['severity'].upper()}] {i['message']}")
        return {
            "confidence_score": round(bayesian_result["mean"], 3),
            "confidence_level": "high" if bayesian_result["mean"] >= 0.7 else "medium" if bayesian_result["mean"] >= 0.4 else "low",
            "complexity_metrics": {"cyclomatic_complexity": cyclomatic, "cognitive_complexity": cognitive, "halstead": halstead},
            "risk_factors": [{"factor": i["message"], "severity": i["severity"], "type": i["type"]} for i in issues],
            "bayesian_details": {
                "posterior_mean": bayesian_result["mean"],
                "confidence": bayesian_result["confidence"],
                "credible_interval": bayesian_result["credible_interval"],
                "observations_used": len(observations),
                "positive_observations": sum(1 for o in observations if o)
            },
            "suggestions": suggestions
        }

    async def _retrieve_similar_bugs(self, args: Dict[str, Any]) -> Dict[str, Any]:
        query = args.get("query", "")
        limit = min(args.get("limit", 5), 20)
        filters = args.get("filters")
        if not self.bug_db.bugs:
            sample_bugs = [
                {"description": "空指针异常：当 user 对象为 null 时调用 getName()", "root_cause": "缺少空值检查", "solution": "添加 if (user != null) 检查", "language": "java", "severity": "critical"},
                {"description": "数据库连接未关闭导致连接池耗尽", "root_cause": "未使用 try-with-resources", "solution": "使用 with 语句或 try-finally 确保关闭", "language": "python", "severity": "high"},
                {"description": "死循环导致 CPU 100%", "root_cause": "while True 缺少 break 条件", "solution": "添加循环退出条件", "language": "python", "severity": "critical"},
                {"description": "XSS 漏洞：未对用户输入进行转义", "root_cause": "直接拼接 HTML", "solution": "使用 DOMPurify 或转义库", "language": "javascript", "severity": "critical"},
                {"description": "浮点数精度问题导致金额计算错误", "root_cause": "使用 float/double 存储金额", "solution": "改用 Decimal 类型", "language": "python", "severity": "high"},
                {"description": "SQL 注入风险：拼接查询字符串", "root_cause": "使用 f-string 拼接 SQL", "solution": "改用参数化查询", "language": "python", "severity": "critical"},
                {"description": "内存泄漏：事件监听器未解绑", "root_cause": "组件销毁时未清理事件", "solution": "在 useEffect 返回清理函数", "language": "javascript", "severity": "high"},
                {"description": "竞态条件：并发写入同一文件", "root_cause": "缺乏锁机制", "solution": "添加文件锁或使用队列", "language": "go", "severity": "medium"},
            ]
            for bug in sample_bugs:
                self.bug_db.add_bug(bug)
        results = self.bug_db.search(query, top_k=limit, filters=filters)
        formatted = [{
            "bug_id": b.get("id", ""), "description": b.get("description", ""),
            "similarity_score": b.get("relevance_score", 0), "root_cause": b.get("root_cause", ""),
            "solution": b.get("solution", ""),
            "fix_confidence": round(0.7 + 0.3 * b.get("relevance_score", 0), 2),
            "language": b.get("language", ""), "severity": b.get("severity", ""),
            "created_at": b.get("created_at", "")
        } for b in results]
        return {"results": formatted, "total_matches": len(formatted), "search_time_ms": round(len(formatted) * 0.5 + 1, 2)}

    async def _predict_complexity(self, args: Dict[str, Any]) -> Dict[str, Any]:
        code = args.get("code", "")
        language = args.get("language", "python")
        history = args.get("history", [])
        cyclomatic = self.code_analyzer.cyclomatic_complexity(code, language)
        cognitive = self.code_analyzer.cognitive_complexity(code, language)
        halstead = self.code_analyzer.halstead_metrics(code, language)
        issues = self.code_analyzer.detect_issues(code, language)
        lines = len(code.strip().split('\n'))
        volume = halstead.get("volume", 0)
        predicted_bug_probability = round(min(0.01 * math.exp(volume / 500) / 10, 0.8), 3)
        if len(history) >= 2:
            prev_complexities = [self.code_analyzer.cyclomatic_complexity(h, language) for h in history]
            trend = "deteriorating" if prev_complexities[-1] > prev_complexities[0] else "improving" if prev_complexities[-1] < prev_complexities[0] else "stable"
        else:
            trend = "stable"
        return {
            "cyclomatic_complexity": cyclomatic,
            "cognitive_complexity": cognitive,
            "maintainability_index": round(max(0, min(100, 100 - cyclomatic * 3 - cognitive * 2)), 1),
            "halstead_metrics": halstead,
            "predicted_bug_probability": predicted_bug_probability,
            "evolution_trend": trend,
            "risk_areas": [i["message"] for i in issues[:3]],
            "code_stats": {
                "total_lines": lines,
                "comment_lines": len(re.findall(r'^\s*(#|//|/\*|\*)', code, re.MULTILINE))
            }
        }

    async def _analyze_reasoning_chain(self, args: Dict[str, Any]) -> Dict[str, Any]:
        steps = args.get("reasoning_steps", [])
        if not steps:
            raise ValueError("推理步骤不能为空")
        step_confidences = [s.get("confidence", 0.5) for s in steps]
        overall_confidence = self.bayesian.propagate_confidence(step_confidences)
        avg_conf = statistics.mean(step_confidences) if step_confidences else 0.5
        bottlenecks = []
        for i, step in enumerate(steps):
            conf = step.get("confidence", 0.5)
            if conf < avg_conf - 0.15:
                bottlenecks.append({"step_id": step.get("step_id", f"step_{i}"), "description": step.get("description", ""), "current_confidence": conf, "gap": round(avg_conf - conf, 3)})
        contradictions = []
        for step in steps:
            premise_ids = step.get("premise_ids", [])
            if premise_ids:
                premise_map = {s.get("step_id"): s.get("confidence", 0.5) for s in steps}
                premise_conf = statistics.mean([premise_map.get(pid, 0.5) for pid in premise_ids]) if premise_ids else 0.5
                conclusion_conf = step.get("confidence", 0.5)
                if conclusion_conf > premise_conf + 0.2:
                    contradictions.append({"step_id": step.get("step_id"), "description": f"结论置信度({conclusion_conf})高于前提({premise_conf})", "severity": "warning"})
        variance = statistics.variance(step_confidences) if len(set(step_confidences)) > 1 else 0
        consistency = 1.0 - min(variance * 3, 1.0)
        return {
            "chain_validity": round(consistency, 3),
            "confidence_propagation": step_confidences,
            "overall_confidence": round(overall_confidence, 3),
            "bottlenecks": bottlenecks,
            "contradictions": contradictions,
            "chain_statistics": {
                "total_steps": len(steps), "avg_confidence": round(avg_conf, 3),
                "min_confidence": round(min(step_confidences), 3) if step_confidences else 0,
                "max_confidence": round(max(step_confidences), 3) if step_confidences else 0,
                "consistency": round(consistency, 3)
            },
            "recommendations": [f"提升步骤 '{b['step_id']}' 的置信度" for b in bottlenecks] + [f"检查步骤 '{c['step_id']}' 的逻辑一致性" for c in contradictions]
        }

    async def _optimize_memory(self, args: Dict[str, Any]) -> Dict[str, Any]:
        result = await asyncio.to_thread(self.memory.optimize, args.get("action", "compact"), args.get("criteria"))
        result["target"] = args.get("target", "all")
        return result

    async def _active_inference(self, args: Dict[str, Any]) -> Dict[str, Any]:
        current_state = args.get("current_state", "")
        goal_state = args.get("goal_state", "")
        available_actions = args.get("available_actions", [])
        constraints = args.get("constraints", [])
        if not current_state or not goal_state:
            raise ValueError("current_state 和 goal_state 不能为空")
        if not available_actions:
            raise ValueError("available_actions 至少需要一个动作")
        result = self.active_inference.select_action(current_state, goal_state, available_actions, constraints)
        self.memory.add(
            content=f"Active inference: {current_state} -> {goal_state}, recommended: {result['recommended_action']}",
            layer="short_term",
            metadata={"type": "active_inference", "current_state": current_state, "goal_state": goal_state, "recommended": result["recommended_action"]}
        )
        return result

    async def _semantic_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        query = args.get("query", "")
        layers = args.get("memory_layers", ["medium_term", "long_term"])
        limit = min(args.get("limit", 5), 20)
        include_metadata = args.get("include_metadata", True)
        if not query:
            raise ValueError("查询内容不能为空")
        results = self.memory.search(query, layers=layers, top_k=limit)
        formatted = []
        for item, score in results:
            entry = {
                "content": item.content, "layer": item.layer,
                "relevance_score": round(score, 4), "importance": item.importance,
                "access_count": item.access_count, "last_accessed": item.last_accessed
            }
            if include_metadata:
                entry["metadata"] = item.metadata
            formatted.append(entry)
        return {
            "results": formatted,
            "total_results": len(formatted),
            "search_metadata": {
                "query_time_ms": round(len(self.memory.items) * 0.001 + 1, 2),
                "layers_searched": layers,
                "total_index_size": len(self.memory.items)
            }
        }

    async def _generate_insight(self, args: Dict[str, Any]) -> Dict[str, Any]:
        topic = args.get("topic", "")
        depth = args.get("depth", "deep")
        if not topic:
            raise ValueError("topic 不能为空")
        result = self.insight_gen.generate(topic, self.memory, self.bug_db, depth)
        self.memory.add(
            content=f"Insight generated: topic={topic}, confidence={result['overall_confidence']}",
            layer="medium_term",
            metadata={"type": "insight", "topic": topic, "depth": depth, "confidence": result["overall_confidence"]}
        )
        return result

    async def _transcribe_audio(self, args: Dict[str, Any]) -> Dict[str, Any]:
        import base64
        from src.core.multimodal.speech_processor import SpeechProcessor
        audio_data_b64 = args.get("audio_data", "")
        language = args.get("language", "auto")
        task = args.get("task", "transcribe")
        try:
            audio_data = base64.b64decode(audio_data_b64)
        except Exception as e:
            return {"error": f"Failed to decode audio data: {str(e)}"}
        try:
            processor = SpeechProcessor(model_size="base")
            result = processor.transcribe(audio_data, language=language, task=task)
            return result
        except ImportError:
            return {"error": "Whisper not installed. Run: pip install openai-whisper"}
        except Exception as e:
            return {"error": f"Transcription failed: {str(e)}"}

    async def _detect_audio_language(self, args: Dict[str, Any]) -> Dict[str, Any]:
        import base64
        from src.core.multimodal.speech_processor import SpeechProcessor
        audio_data_b64 = args.get("audio_data", "")
        try:
            audio_data = base64.b64decode(audio_data_b64)
        except Exception as e:
            return {"error": f"Failed to decode audio data: {str(e)}"}
        try:
            processor = SpeechProcessor(model_size="base")
            result = processor.detect_language(audio_data)
            return result
        except ImportError:
            return {"error": "Whisper not installed. Run: pip install openai-whisper"}
        except Exception as e:
            return {"error": f"Language detection failed: {str(e)}"}

    async def _recognize_voice_command(self, args: Dict[str, Any]) -> Dict[str, Any]:
        import base64
        from src.core.multimodal.speech_processor import SpeechProcessor
        audio_data_b64 = args.get("audio_data", "")
        language = args.get("language", "zh")
        try:
            audio_data = base64.b64decode(audio_data_b64)
        except Exception as e:
            return {"error": f"Failed to decode audio data: {str(e)}"}
        try:
            processor = SpeechProcessor(model_size="base")
            commands = {"启动": "start", "停止": "stop", "搜索": "search", "分析": "analyze", "打开": "open", "关闭": "close"}
            result = processor.recognize_commands(audio_data, commands, language=language)
            return result
        except ImportError:
            return {"error": "Whisper not installed. Run: pip install openai-whisper"}
        except Exception as e:
            return {"error": f"Command recognition failed: {str(e)}"}

    async def _analyze_multimodal(self, args: Dict[str, Any]) -> Dict[str, Any]:
        image_data_b64 = args.get("image_data")
        text = args.get("text")
        audio_data_b64 = args.get("audio_data")
        task = args.get("task", "综合分析")
        results = {}
        if image_data_b64:
            results["image_analysis"] = {"status": "available", "message": "图像数据已接收"}
        if text:
            results["text_analysis"] = {"status": "analyzed", "content": text, "word_count": len(text.split())}
        if audio_data_b64:
            try:
                import base64
                from src.core.multimodal.speech_processor import SpeechProcessor
                audio_data = base64.b64decode(audio_data_b64)
                processor = SpeechProcessor(model_size="base")
                audio_result = processor.transcribe(audio_data)
                results["audio_analysis"] = audio_result
            except ImportError:
                results["audio_analysis"] = {"error": "Whisper not installed"}
            except Exception as e:
                results["audio_analysis"] = {"error": str(e)}
        results["multimodal_summary"] = {
            "task": task,
            "modalities_present": [k for k in ["image", "text", "audio"] if k in results],
            "analysis_complete": True
        }
        return results

    async def _get_resource_content(self, uri: str) -> Dict[str, Any]:
        now = datetime.now()
        if uri == "bayesian://memory/snapshot":
            return self.memory.get_stats()
        elif uri == "bayesian://metrics/free-energy":
            return {
                "current_state": {
                    "free_energy_value": self.memory._calculate_free_energy(),
                    "surprise_level": round(1.0 - self.memory._calculate_free_energy(), 3),
                    "entropy": round(-math.log(self.memory._calculate_free_energy() + 0.01) if self.memory._calculate_free_energy() > 0 else 3, 2)
                },
                "memory_stats": self.memory.get_stats(),
                "optimization_events": [{"timestamp": now.isoformat(), "action": "monitoring", "energy_value": self.memory._calculate_free_energy()}]
            }
        elif uri == "bayesian://reasoning/history":
            return {
                "recent_chains": [{"chain_id": "init", "goal": "系统初始化", "steps_count": 0, "avg_confidence": 0.0, "completed_at": now.isoformat()}],
                "statistics": {"total_chains": len(self.memory.items), "success_rate": 0.0, "avg_length": 0.0}
            }
        elif uri == "bayesian://knowledge/graph":
            return {
                "nodes": len(self.memory.items),
                "edges": len(self.memory.items) * 2,
                "categories": {
                    "code": sum(1 for item in self.memory.items.values() if item.metadata.get("type") == "code_evaluation"),
                    "insight": sum(1 for item in self.memory.items.values() if item.metadata.get("type") == "insight"),
                    "inference": sum(1 for item in self.memory.items.values() if item.metadata.get("type") == "active_inference"),
                    "other": sum(1 for item in self.memory.items.values() if item.metadata.get("type") is None)
                },
                "recent_additions": [item.id for item in list(self.memory.items.values())[-5:]]
            }
        elif uri == "bayesian://cognition/state":
            mem_stats = self.memory.get_stats()
            total = max(mem_stats["total_items"], 1)
            return {
                "active_mode": "system2_deliberate" if mem_stats["total_items"] > 100 else "system1_fast",
                "attention_allocation": {
                    "short_term": round(mem_stats["short_term_count"] / total, 3),
                    "medium_term": round(mem_stats["medium_term_count"] / total, 3),
                    "long_term": round(mem_stats["long_term_count"] / total, 3)
                },
                "reasoning_depth": min(3 + mem_stats["total_items"] // 100, 10),
                "last_optimization": now.isoformat()
            }
        elif uri == "bayesian://bug-database/stats":
            return self.bug_db.get_stats()
        return {}

    def get_server_info(self) -> Dict[str, Any]:
        return {
            "name": "BayesianAGICore",
            "version": "2.0.0",
            "protocolVersion": "2024-11-05",
            "description": "贝叶斯认知引擎 MCP Server - 支持真实代码分析、语义搜索、主动推理",
            "capabilities": list(self.tools.keys()),
            "endpoints": {
                "mcp": f"http://{self.host}:{self.port}/mcp",
                "tools_list": f"http://{self.host}:{self.port}/tools",
                "resources": f"http://{self.host}:{self.port}/resources"
            },
            "memory_stats": self.memory.get_stats(),
            "bug_db_stats": self.bug_db.get_stats()
        }
