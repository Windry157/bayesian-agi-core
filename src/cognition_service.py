#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cognition Service
处理与认知相关的请求
"""

import os
import logging
from fastapi import FastAPI, HTTPException
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
    title="Bayesian-AGI-Core Cognition Service",
    description="Cognition Service for Bayesian-AGI-Core",
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
    logger.info("开始启动Cognition服务...")
    config = load_config()
    # 初始化智能助理
    await assistant.initialize(config)
    logger.info("Cognition服务启动成功")


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "message": "Cognition Service is running"}


# 做出决策
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
        "message": "Welcome to Bayesian-AGI-Core Cognition Service",
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

    uvicorn.run("src.cognition_service", host="0.0.0.0", port=8003, reload=True)
