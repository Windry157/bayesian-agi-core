#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM Service
处理与LLM相关的请求
"""

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.utils.config import load_config
from src.core.assistant import Assistant
from src.core.monitoring import monitoring

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="Bayesian-AGI-Core LLM Service",
    description="LLM Service for Bayesian-AGI-Core",
    version="1.0.0",
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# 创建智能助理实例
assistant = Assistant()


# 启动事件
@app.on_event("startup")
async def startup_event():
    """启动事件"""
    logger.info("开始启动LLM服务...")
    config = load_config()
    # 初始化智能助理
    await assistant.initialize(config)
    logger.info("LLM服务启动成功")


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "message": "LLM Service is running"}


# 获取模型列表
@app.get("/api/models")
async def get_models():
    """获取模型列表"""
    models = assistant.get_models()
    logger.info(f"返回的模型列表: {models}")
    return {"models": models}


# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Welcome to Bayesian-AGI-Core LLM Service",
        "version": "1.0.0",
        "docs": "/docs",
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

    uvicorn.run("src.llm_service", host="0.0.0.0", port=8001, reload=True)
