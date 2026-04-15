#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI应用主入口
"""

import asyncio
import logging
import time
import psutil
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from src.utils.config import load_config
from src.core.assistant import Assistant
from src.core.monitoring import monitoring

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="Bayesian-AGI-Core",
    description="基于自由能原理和主动推理的认知智能体",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# # 添加监控中间件
# @app.middleware("http")
# async def add_process_time_header(request: Request, call_next):
#     start_time = time.time()
#     response = await call_next(request)
#     process_time = time.time() - start_time
#     
#     # 记录请求
#     await monitoring.async_record_request(
#         method=request.method,
#         endpoint=request.url.path,
#         status=response.status_code,
#         duration=process_time
#     )
#     
#     # 记录系统资源使用情况
#     monitoring.record_memory_usage(psutil.virtual_memory().used)
#     monitoring.record_cpu_usage(psutil.cpu_percent())
#     
#     return response

# 创建智能助理实例
assistant = Assistant()

# 启动事件
@app.on_event("startup")
async def startup_event():
    """启动事件"""
    logger.info("开始启动智能助理...")
    config = load_config()
    logger.info(f"加载的配置: {config}")
    await assistant.initialize(config)
    
    # 注册Ollama服务
    try:
        from src.core.llm.ollama_service import OllamaLLM
        ollama_config = config.get("models", {})
        if ollama_config:
            llm_service = OllamaLLM(ollama_config)
            assistant.register_service("llm", llm_service)
            logger.info("Ollama LLM 服务注册成功")
        # Fallback to OpenAI
    except Exception as e:
        logger.error(f"LLM 服务注册失败: {e}")

# 健康检查
@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "message": "Bayesian-AGI-Core is running"}

# 获取模型列表
@app.get("/api/models")
async def get_models():
    """获取模型列表"""
    models = assistant.get_models()
    logger.info(f"返回的模型列表: {models}")
    return {"models": models}

# 添加记忆
@app.post("/api/memory")
async def add_memory(content: str, metadata: dict = None):
    """添加记忆"""
    try:
        memory_id = await assistant.add_memory(content, metadata)
        return {"id": memory_id, "message": "Memory added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add memory: {e}")

# 检索记忆
@app.get("/api/memory/search")
async def search_memory(query: str, top_k: int = 5):
    """检索记忆"""
    try:
        memories = await assistant.retrieve_memories(query, top_k)
        return {"memories": memories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search memory: {e}")

# 决策接口
@app.post("/api/decision")
async def make_decision(possible_actions: list):
    """做出决策"""
    try:
        decision = assistant.make_decision(possible_actions)
        return {"decision": decision}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to make decision: {e}")

# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Welcome to Bayesian-AGI-Core",
        "version": "1.0.0",
        "docs": "/docs"
    }

# Prometheus指标端点
@app.get("/health/metrics")
def metrics():
    """Prometheus指标端点"""
    try:
        # 简单的指标数据
        return """
# HELP http_requests_total Total HTTP Requests
# TYPE http_requests_total counter
http_requests_total 100

# HELP http_request_duration_seconds HTTP Request Duration
# TYPE http_request_duration_seconds histogram
test_metric 42
"""
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        return f"Error: {str(e)}"

if __name__ == "__main__":
    import uvicorn
    config = load_config()
    server_config = config.get("server", {})
    host = server_config.get("host", "0.0.0.0")
    port = server_config.get("port", 8000)
    workers = server_config.get("workers", 4)
    
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        workers=workers,
        reload=True
    )
