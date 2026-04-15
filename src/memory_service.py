#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory Service
处理与记忆相关的请求
"""

import os
import logging
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
from src.utils.config import load_config
from src.core.assistant import Assistant
from src.utils.message_queue import message_queue_manager
from src.core.monitoring import monitoring

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="Bayesian-AGI-Core Memory Service",
    description="Memory Service for Bayesian-AGI-Core",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# 定义请求模型
class MemoryRequest(BaseModel):
    content: str
    metadata: Optional[Dict] = None

# 创建智能助理实例
assistant = Assistant()

# 消息处理函数
def handle_memory_message(message):
    """处理记忆相关的消息"""
    try:
        message_type = message.get("type")
        if message_type == "add_memory":
            content = message.get("content")
            metadata = message.get("metadata")
            # 异步添加记忆
            asyncio.create_task(assistant.add_memory(content, metadata))
            logger.info(f"处理添加记忆消息: {content}")
        elif message_type == "retrieve_memories":
            query = message.get("query")
            top_k = message.get("top_k", 5)
            # 异步检索记忆
            asyncio.create_task(assistant.retrieve_memories(query, top_k))
            logger.info(f"处理检索记忆消息: {query}")
        else:
            logger.warning(f"未知消息类型: {message_type}")
    except Exception as e:
        logger.error(f"处理消息失败: {e}")

# 启动事件
@app.on_event("startup")
async def startup_event():
    """启动事件"""
    logger.info("开始启动Memory服务...")
    config = load_config()
    # 初始化智能助理
    await assistant.initialize(config)
    
    # 初始化消息队列
    try:
        message_queue_manager.connect()
        # 订阅记忆相关的消息
        message_queue_manager.subscribe("memory_queue", handle_memory_message)
        # 启动消息消费
        asyncio.create_task(asyncio.to_thread(message_queue_manager.start_consuming))
        logger.info("消息队列初始化成功")
    except Exception as e:
        logger.warning(f"消息队列初始化失败: {e}")
    
    logger.info("Memory服务启动成功")

# 健康检查
@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "message": "Memory Service is running"}

# 添加记忆
@app.post("/api/memory")
async def add_memory(req: MemoryRequest):
    """添加记忆"""
    try:
        memory_id = await assistant.add_memory(
            content=req.content,
            metadata=req.metadata  # 已在下层清理空字典
        )
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

# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Welcome to Bayesian-AGI-Core Memory Service",
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
    uvicorn.run(
        "src.memory_service:app",
        host="0.0.0.0",
        port=8002,
        reload=True
    )
