#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bayesian-AGI-Core Web UI - Advanced OpenCode-like Interface
Features:
- Hybrid Search (Vector + BM25)
- Knowledge Graph Integration
- Conversation History Management
- Query Rewriting
- Structured Output
- Self-Reflection
- Agent Framework (Task Planning & Execution)
"""

import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from typing import List, Dict, Any, Optional
import json
import httpx
import os
import tempfile
from datetime import datetime

from src.core.memory import MemorySystem
from src.core.code import CodeAnalyzer, CodeGenerator
from src.core.knowledge import (
    RAGRetriever, 
    HybridSearchEngine,
    QueryRewriter,
    StructuredOutputFormatter,
    SelfReflectionChecker,
    EnhancedRAGRetriever
)
from src.core.conversation import ConversationManager
from src.core.agent import Agent, SimpleAgent, KnowledgeBaseTool, CodeAnalysisTool, MemoryTool, CalculatorTool
from src.core.knowledge_graph import KnowledgeGraph, GraphQueryEngine
from src.core.evaluation import QualityEvaluator, RAGTestFramework
from src.core.cache import CacheManager, CacheConfig
from src.core.monitoring import MetricsCollector, AlertManager, AlertRule, AlertSeverity, SystemMonitor
from src.core.filesystem import FileBridge, FileBridgeConfig

app = FastAPI(title="Bayesian-AGI-Core Web UI", version="5.3.0")

memory_system = None
code_generator = None
rag_retriever = None
hybrid_search = None
enhanced_rag = None
query_rewriter = None
conversation_manager = None
agent = None
simple_agent = None
knowledge_graph = None
quality_evaluator = None
test_framework = None
cache_manager = None
metrics_collector = None
alert_manager = None
system_monitor = None
file_bridge = None

@app.on_event("startup")
async def startup_event():
    global memory_system, code_generator, rag_retriever, hybrid_search, enhanced_rag, query_rewriter
    global conversation_manager, agent, simple_agent, knowledge_graph, quality_evaluator, test_framework
    global cache_manager, metrics_collector, alert_manager, system_monitor, file_bridge
    
    memory_system = MemorySystem()
    code_generator = CodeGenerator()
    rag_retriever = RAGRetriever(memory_system.vector_index)
    hybrid_search = HybridSearchEngine(memory_system.vector_index)
    knowledge_graph = KnowledgeGraph()
    enhanced_rag = EnhancedRAGRetriever(memory_system.vector_index, knowledge_graph)
    query_rewriter = QueryRewriter()
    conversation_manager = ConversationManager(
        max_history=20,
        max_tokens=4000,
        summarize_threshold=10
    )
    quality_evaluator = QualityEvaluator()
    test_framework = RAGTestFramework()
    
    cache_manager = CacheManager(CacheConfig(use_redis=False, default_ttl=3600))
    await cache_manager.initialize()
    
    metrics_collector = MetricsCollector()
    alert_manager = AlertManager(metrics_collector)
    for rule in alert_manager.get_default_rules():
        alert_manager.add_rule(rule)
    await alert_manager.start(check_interval=10)
    
    system_monitor = SystemMonitor(metrics_collector)
    await system_monitor.start(interval=5)
    
    file_bridge = FileBridge(FileBridgeConfig(
        root_path="./data",
        max_file_size_bytes=10*1024*1024,
        enable_auth=True,
        allow_anonymous_read=True
    ))
    
    agent = Agent()
    simple_agent = SimpleAgent()
    
    knowledge_tool = KnowledgeBaseTool(hybrid_search, rag_retriever)
    code_tool = CodeAnalysisTool(code_generator)
    memory_tool = MemoryTool(memory_system)
    calc_tool = CalculatorTool()
    
    agent.register_tool(knowledge_tool)
    agent.register_tool(code_tool)
    agent.register_tool(memory_tool)
    agent.register_tool(calc_tool)
    
    simple_agent.register_tool(knowledge_tool)
    simple_agent.register_tool(code_tool)
    simple_agent.register_tool(memory_tool)
    simple_agent.register_tool(calc_tool)
    
    print("[OK] Advanced Web UI 启动完成 (v5.3)")
    print("    - Hybrid Search: Enabled")
    print("    - Knowledge Graph: Enabled")
    print("    - Conversation History: Enabled")
    print("    - Query Rewriting: Enabled")
    print("    - Structured Output: Enabled")
    print("    - Agent Framework: Enabled")
    print("    - Evaluation Framework: Enabled")
    print("    - Cache: Enabled (Memory)")
    print("    - Monitoring: Enabled")
    print("    - Alert System: Enabled")
    print("    - File Bridge: Enabled")

@app.on_event("shutdown")
async def shutdown_event():
    if memory_system:
        await memory_system.close()
    if cache_manager:
        await cache_manager.close()
    if alert_manager:
        await alert_manager.stop()
    if system_monitor:
        await system_monitor.stop()
    print("[OK] Advanced Web UI 关闭完成")

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("webui/templates/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

async def call_ollama(messages: List[Dict[str, str]]) -> str:
    try:
        url = "http://192.168.3.105:11434/api/chat"
        payload = {
            "model": "llama3.1:8b",
            "messages": messages,
            "stream": False
        }
        
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")
    except Exception as e:
        print(f"LLM调用失败: {e}")
        return f"抱歉，暂时无法连接到AI服务。错误: {str(e)}"

@app.post("/api/chat")
async def chat(request: Dict[str, Any]):
    messages = request.get("messages", [])
    session_id = request.get("session_id", "default")
    use_rag = request.get("use_rag", True)
    use_history = request.get("use_history", True)
    use_query_rewrite = request.get("use_query_rewrite", True)
    use_graph = request.get("use_graph", True)
    
    user_message = messages[-1]["content"] if messages else ""
    
    if use_history:
        conversation_manager.add_message(session_id, "user", user_message)
    
    context_messages = []
    sources = []
    
    if use_rag:
        query = user_message
        if use_query_rewrite and query_rewriter:
            history_context = ""
            if use_history:
                history_context = "\n".join([
                    f"{m['role']}: {m['content']}"
                    for m in conversation_manager.get_context(session_id, include_summary=False)[-3:]
                ])
            query = await query_rewriter.rewrite_query(user_message, history_context)
        
        if use_graph and enhanced_rag:
            enhanced_result = await enhanced_rag.enhanced_query(query, top_k=3, use_graph=True)
            context = enhanced_result.get('context', '')
            sources = enhanced_result.get('sources', [])
        else:
            results = await hybrid_search.hybrid_search(
                query, 
                top_k=3,
                vector_weight=0.7,
                keyword_weight=0.3
            )
            if results:
                context = "\n\n".join([
                    f"【{r['source']}】(相关度: {r['combined_score']:.2f})\n{r['content'][:300]}..."
                    for r in results
                ])
                sources = [
                    {
                        "name": r['source'],
                        "score": round(r['combined_score'], 3),
                        "type": "document"
                    }
                    for r in results
                ]
            else:
                context = ""
        
        if context:
            context_prompt = f"""
参考以下文档内容和知识图谱关系来回答问题。如果参考内容中没有相关信息，请明确说明。

{context}

---
参考资料：{', '.join([s.get('name', s.get('source', '未知')) for s in sources])}
"""
            context_messages.append({"role": "system", "content": context_prompt})
    
    if use_history:
        history = conversation_manager.get_context(session_id, include_summary=True, max_turns=10)
        context_messages.extend(history)
    
    context_messages.extend(messages)
    
    response = await call_ollama(context_messages)
    
    if use_history:
        conversation_manager.add_message(session_id, "assistant", response)
    
    result = {
        "response": response,
        "is_tool": False,
        "sources": sources
    }
    
    if use_query_rewrite and query_rewriter:
        result["query_rewritten"] = query
    
    return result

@app.post("/api/agent/run")
async def run_agent(request: Dict[str, Any]):
    task = request.get("task", "")
    max_steps = request.get("max_steps", 10)
    
    if not task:
        return {"success": False, "error": "任务不能为空"}
    
    state = await agent.run(task, max_steps=max_steps)
    
    return {
        "success": True,
        "task": state.task,
        "is_complete": state.is_complete,
        "steps": len(state.thoughts),
        "final_answer": state.final_answer,
        "trace": agent.get_trace()
    }

@app.post("/api/agent/plan")
async def plan_task(request: Dict[str, Any]):
    task = request.get("task", "")
    
    if not task:
        return {"success": False, "error": "任务不能为空"}
    
    result = await simple_agent.plan_and_execute(task)
    
    return result

@app.get("/api/agent/tools")
async def get_tools():
    tools_info = []
    for name, tool in agent.tools.items():
        tools_info.append({
            "name": tool.name,
            "description": tool.description
        })
    
    return {"tools": tools_info}

@app.get("/api/graph/stats")
async def get_graph_stats():
    """获取知识图谱统计"""
    return enhanced_rag.get_graph_stats() if enhanced_rag else {"error": "Graph not initialized"}

@app.get("/api/graph/triples")
async def get_triples():
    """获取知识图谱三元组"""
    return {
        "triples": enhanced_rag.knowledge_graph.query_triples() if enhanced_rag else []
    }

@app.get("/api/graph/export")
async def export_graph():
    """导出知识图谱"""
    return {
        "graph_text": enhanced_rag.export_graph_as_text() if enhanced_rag else "Graph not initialized"
    }

@app.post("/api/graph/query")
async def query_graph(request: Dict[str, Any]):
    """图谱查询"""
    query = request.get("query", "")
    entity1 = request.get("entity1")
    entity2 = request.get("entity2")
    
    result = await enhanced_rag.query_with_graph_reasoning(
        query,
        entity1=entity1,
        entity2=entity2
    )
    
    return result

@app.post("/api/graph/entity/{entity_name}/related")
async def get_related_entities(entity_name: str):
    """获取实体的相关实体"""
    engine = GraphQueryEngine(enhanced_rag.knowledge_graph) if enhanced_rag else None
    if not engine:
        return {"error": "Graph not initialized"}
    
    related = engine.find_related_entities(entity_name, max_depth=2)
    return {"entity": entity_name, "related": related}

@app.post("/api/chat/structured")
async def chat_structured(request: Dict[str, Any]):
    messages = request.get("messages", [])
    schema = request.get("schema", {})
    task = request.get("task", "请提取信息")
    
    user_message = messages[-1]["content"] if messages else ""
    
    rag_result = await hybrid_search.hybrid_search(user_message, top_k=3)
    
    context = "\n\n".join([f"【{r['source']}】\n{r['content']}" for r in rag_result])
    
    prompt = StructuredOutputFormatter.generate_extraction_prompt(task, context, schema)
    
    response = await call_ollama([
        {"role": "system", "content": "你是一个专业的信息提取助手。请严格按照要求提取信息。"},
        {"role": "user", "content": prompt}
    ])
    
    return {
        "response": response,
        "sources": [r['source'] for r in rag_result],
        "raw_context": context
    }

@app.post("/api/chat/refine")
async def refine_answer(request: Dict[str, Any]):
    question = request.get("question", "")
    context = request.get("context", "")
    answer = request.get("answer", "")
    
    checker = SelfReflectionChecker()
    check_result = await checker.check_answer(question, context, answer)
    
    if check_result.get("needs_revision", False):
        refine_prompt = f"""
请根据以下反馈优化答案：

原始问题：{question}

参考内容：
{context}

原始答案：
{answer}

问题反馈：{', '.join(check_result.get('issues', []))}

改进建议：{', '.join(check_result.get('improvements', []))}

请生成优化后的答案。
"""
        
        refined = await call_ollama([
            {"role": "system", "content": "你是一个专业的答案优化专家。"},
            {"role": "user", "content": refine_prompt}
        ])
        
        return {
            "original_answer": answer,
            "refined_answer": refined,
            "quality_score": check_result.get("quality_score", 5),
            "issues": check_result.get("issues", []),
            "improvements": check_result.get("improvements", [])
        }
    
    return {
        "original_answer": answer,
        "refined_answer": answer,
        "quality_score": check_result.get("quality_score", 5),
        "issues": check_result.get("issues", []),
        "improvements": check_result.get("improvements", []),
        "message": "答案质量良好，无需优化"
    }

@app.post("/api/code/generate")
async def generate_code(request: Dict[str, Any]):
    prompt = request.get("prompt", "")
    language = request.get("language", "python")
    result = await code_generator.generate_code(prompt, language)
    return {"code": result}

@app.post("/api/code/analyze")
async def analyze_code(request: Dict[str, Any]):
    code = request.get("code", "")
    complexity = CodeAnalyzer.analyze_complexity(code)
    errors = CodeAnalyzer.detect_errors(code)
    return {"complexity": complexity, "errors": errors}

@app.post("/api/code/optimize")
async def optimize_code(request: Dict[str, Any]):
    code = request.get("code", "")
    result = await code_generator.optimize_code(code)
    return {"code": result}

@app.post("/api/code/debug")
async def debug_code(request: Dict[str, Any]):
    code = request.get("code", "")
    error = request.get("error", "")
    result = await code_generator.debug_code(code, error)
    return {"code": result}

@app.post("/api/code/explain")
async def explain_code(request: Dict[str, Any]):
    code = request.get("code", "")
    result = await code_generator.explain_code(code)
    return {"explanation": result}

@app.post("/api/code/test")
async def generate_test(request: Dict[str, Any]):
    code = request.get("code", "")
    result = await code_generator.generate_test(code)
    return {"test": result}

@app.post("/api/code/document")
async def generate_documentation(request: Dict[str, Any]):
    code = request.get("code", "")
    result = await code_generator.generate_documentation(code)
    return {"documentation": result}

@app.post("/api/knowledge/upload")
async def upload_document(file: UploadFile = File(...)):
    allowed_extensions = ['.pdf', '.docx', '.md', '.txt']
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        return {"success": False, "error": f"不支持的文件类型: {file_ext}，支持: {', '.join(allowed_extensions)}"}
    
    try:
        with tempfile.NamedTemporaryFile(mode='wb', suffix=file_ext, delete=False) as f:
            f.write(await file.read())
            temp_path = f.name
        
        result = await enhanced_rag.add_document_with_graph(temp_path, use_graph=True)
        os.unlink(temp_path)
        
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/knowledge/documents")
async def get_documents():
    return {"documents": rag_retriever.get_document_list()}

@app.delete("/api/knowledge/documents/{doc_id}")
async def delete_document(doc_id: str):
    success = await rag_retriever.delete_document(doc_id)
    return {"success": success}

@app.get("/api/conversation/{session_id}")
async def get_conversation_info(session_id: str):
    info = conversation_manager.get_conversation_info(session_id)
    return info if info else {"error": "会话不存在"}

@app.delete("/api/conversation/{session_id}")
async def clear_conversation(session_id: str):
    conversation_manager.clear_conversation(session_id)
    return {"success": True}

@app.post("/api/evaluation/quality")
async def evaluate_answer_quality(request: Dict[str, Any]):
    """评估回答质量"""
    if not quality_evaluator:
        return {"error": "Evaluator not initialized"}
    
    question = request.get("question", "")
    context = request.get("context", "")
    answer = request.get("answer", "")
    retrieved_chunks = request.get("retrieved_chunks", None)
    
    quality_score = await quality_evaluator.evaluate(
        question,
        context,
        answer,
        retrieved_chunks
    )
    
    return {
        "overall_score": quality_score.overall_score,
        "faithfulness": quality_score.faithfulness.overall_score,
        "relevance": quality_score.relevance.overall_relevance_score,
        "clarity": quality_score.clarity_score,
        "completeness": quality_score.completeness_score,
        "coherence": quality_score.coherence_score,
        "explanation": quality_score.explanation,
        "strengths": quality_score.strengths,
        "weaknesses": quality_score.weaknesses,
        "suggestions": quality_score.suggestions
    }

@app.post("/api/evaluation/test")
async def run_test_case(request: Dict[str, Any]):
    """运行单个测试用例"""
    if not test_framework:
        return {"error": "Test framework not initialized"}
    
    question = request.get("question", "")
    context = request.get("context", "")
    
    test_result = await test_framework.generate_answer(question, context)
    
    return {
        "question": question,
        "context": context,
        "answer": test_result
    }

@app.get("/api/evaluation/report")
async def get_evaluation_report():
    """获取评估报告"""
    if not test_framework:
        return {"error": "Test framework not initialized"}
    
    test_framework.add_sample_test_cases()
    report = await test_framework.run_all_tests()
    test_framework.print_summary(report)
    
    return {
        "test_cases_run": report.test_cases_run,
        "successful_tests": report.successful_tests,
        "failed_tests": report.failed_tests,
        "average_score": report.average_score,
        "min_score": report.min_score,
        "max_score": report.max_score,
        "timestamp": report.timestamp,
        "results": [
            {
                "question": r.test_case.question,
                "answer": r.generated_answer,
                "score": r.score,
                "success": r.success
            }
            for r in report.results
        ]
    }

@app.get("/api/memory")
async def get_memory_stats():
    return memory_system.get_stats()

@app.post("/api/memory/add")
async def add_memory(request: Dict[str, Any]):
    content = request.get("content", "")
    importance = request.get("importance", 1.0)
    await memory_system.add_memory(content, importance=importance)
    return {"status": "success"}

@app.post("/api/memory/search")
async def search_memory(request: Dict[str, Any]):
    query = request.get("query", "")
    results = await memory_system.retrieve_memories(query)
    return {"results": results}

@app.get("/api/cache/stats")
async def get_cache_stats():
    """获取缓存统计信息"""
    if not cache_manager:
        return {"error": "Cache manager not initialized"}
    stats = await cache_manager.get_stats()
    return {"cache": stats}

@app.post("/api/cache/clear")
async def clear_cache():
    """清空缓存"""
    if not cache_manager:
        return {"error": "Cache manager not initialized"}
    await cache_manager.clear_all()
    return {"status": "success", "message": "Cache cleared"}

@app.get("/api/monitoring/metrics")
async def get_monitoring_metrics():
    """获取监控指标"""
    if not metrics_collector:
        return {"error": "Metrics collector not initialized"}
    metrics = await metrics_collector.get_all_metrics()
    return {"metrics": metrics}

@app.get("/api/monitoring/system")
async def get_system_metrics():
    """获取系统指标"""
    if not system_monitor:
        return {"error": "System monitor not initialized"}
    metrics = await system_monitor.get_system_metrics()
    return {"system": metrics.to_dict()}

@app.get("/api/monitoring/alerts/active")
async def get_active_alerts():
    """获取活跃告警"""
    if not alert_manager:
        return {"error": "Alert manager not initialized"}
    alerts = await alert_manager.get_active_alerts()
    return {"alerts": [a.to_dict() for a in alerts]}

@app.get("/api/monitoring/alerts/history")
async def get_alert_history(limit: int = 100):
    """获取告警历史"""
    if not alert_manager:
        return {"error": "Alert manager not initialized"}
    alerts = await alert_manager.get_alert_history(limit)
    return {"alerts": [a.to_dict() for a in alerts]}

@app.post("/api/files/auth")
async def authenticate_user(request: Dict[str, Any]):
    """用户认证"""
    if not file_bridge:
        return {"error": "File bridge not initialized"}
    
    username = request.get("username", "")
    password = request.get("password", "")
    
    token = file_bridge.authenticate(username, password)
    if token:
        return {"success": True, "token": token, "username": username}
    return {"success": False, "error": "用户名或密码错误"}

@app.get("/api/files/list")
async def list_directory(path: str = "", token: str = ""):
    """列出目录内容"""
    if not file_bridge:
        return {"error": "File bridge not initialized"}
    
    try:
        items = file_bridge.list_directories(path, token)
        return {"items": [item.to_dict() for item in items]}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/files/content")
async def read_file(path: str, token: str = ""):
    """读取文件内容"""
    if not file_bridge:
        return {"error": "File bridge not initialized"}
    
    try:
        content = file_bridge.read_file_content(path, token)
        return content.to_dict()
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/files/write")
async def write_file(request: Dict[str, Any]):
    """写入文件内容"""
    if not file_bridge:
        return {"error": "File bridge not initialized"}
    
    try:
        path = request.get("path", "")
        content = request.get("content", "")
        token = request.get("token", "")
        
        success = file_bridge.write_file_content(path, content, token)
        return {"success": success}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/files/metadata")
async def get_file_metadata(path: str, token: str = ""):
    """获取文件元数据"""
    if not file_bridge:
        return {"error": "File bridge not initialized"}
    
    try:
        metadata = file_bridge.get_file_metadata(path, token)
        return metadata.to_dict()
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/files/mkdir")
async def create_directory(request: Dict[str, Any]):
    """创建目录"""
    if not file_bridge:
        return {"error": "File bridge not initialized"}
    
    try:
        path = request.get("path", "")
        token = request.get("token", "")
        
        success = file_bridge.create_directory(path, token)
        return {"success": success}
    except Exception as e:
        return {"error": str(e)}

@app.delete("/api/files/delete")
async def delete_file(path: str, token: str = ""):
    """删除文件/目录"""
    if not file_bridge:
        return {"error": "File bridge not initialized"}
    
    try:
        success = file_bridge.delete_file(path, token)
        return {"success": success}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/files/rename")
async def rename_file(request: Dict[str, Any]):
    """重命名文件/目录"""
    if not file_bridge:
        return {"error": "File bridge not initialized"}
    
    try:
        old_path = request.get("old_path", "")
        new_path = request.get("new_path", "")
        token = request.get("token", "")
        
        success = file_bridge.rename_file(old_path, new_path, token)
        return {"success": success}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/files/copy")
async def copy_file(request: Dict[str, Any]):
    """复制文件/目录"""
    if not file_bridge:
        return {"error": "File bridge not initialized"}
    
    try:
        source = request.get("source", "")
        dest = request.get("dest", "")
        token = request.get("token", "")
        
        success = file_bridge.copy_file(source, dest, token)
        return {"success": success}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/files/tree")
async def get_directory_tree(path: str = "", depth: int = 3, token: str = ""):
    """获取目录树"""
    if not file_bridge:
        return {"error": "File bridge not initialized"}
    
    try:
        tree = file_bridge.get_tree(path, depth, token)
        return {"tree": tree}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/files/exists")
async def file_exists(path: str, token: str = ""):
    """检查文件是否存在"""
    if not file_bridge:
        return {"error": "File bridge not initialized"}
    
    exists = file_bridge.exists(path, token)
    return {"exists": exists}

@app.get("/api/files/stats")
async def get_filesystem_stats():
    """获取文件系统统计信息"""
    if not file_bridge:
        return {"error": "File bridge not initialized"}
    
    stats = file_bridge.get_stats()
    return {"stats": stats}

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            response = await chat({"messages": [message]})
            await websocket.send_text(json.dumps(response))
    except WebSocketDisconnect:
        print("WebSocket disconnected")

app.mount("/static", StaticFiles(directory="webui/static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)