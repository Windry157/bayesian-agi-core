#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Gateway
处理所有HTTP请求并路由到相应的微服务
"""

import os
import logging
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
from src.utils.message_queue import message_queue_manager
from src.utils.http_client import http_client_manager
from src.core.monitoring import monitoring

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="Bayesian-AGI-Core API Gateway",
    description="API Gateway for Bayesian-AGI-Core microservices",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# 服务URLs
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://localhost:8001")
MEMORY_SERVICE_URL = os.getenv("MEMORY_SERVICE_URL", "http://localhost:8002")
COGNITION_SERVICE_URL = os.getenv("COGNITION_SERVICE_URL", "http://localhost:8003")
VISION_SERVICE_URL = os.getenv("VISION_SERVICE_URL", "http://localhost:8004")
MULTIMODAL_SERVICE_URL = os.getenv("MULTIMODAL_SERVICE_URL", "http://localhost:8005")

# 定义请求模型
class MemoryRequest(BaseModel):
    content: str
    metadata: Optional[Dict] = None

# 启动事件
@app.on_event("startup")
async def startup_event():
    """启动事件"""
    logger.info("开始启动API Gateway...")
    # 初始化消息队列
    try:
        message_queue_manager.connect()
        logger.info("消息队列初始化成功")
    except Exception as e:
        logger.warning(f"消息队列初始化失败: {e}")
    logger.info("API Gateway启动成功")

# 健康检查
@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "message": "API Gateway is running"}

# 服务健康检查
@app.get("/health/services")
async def services_health_check():
    """检查所有微服务的健康状态"""
    services = {
        "llm_service": LLM_SERVICE_URL,
        "memory_service": MEMORY_SERVICE_URL,
        "cognition_service": COGNITION_SERVICE_URL,
        "vision_service": VISION_SERVICE_URL,
        "multimodal_service": MULTIMODAL_SERVICE_URL
    }
    
    health_status = {}
    for service_name, service_url in services.items():
        try:
            client = await http_client_manager.get_client(service_url)
            response = await client.get("/health")
            if response.status_code == 200:
                health_status[service_name] = {"status": "ok", "message": "Service is running"}
            else:
                health_status[service_name] = {"status": "error", "message": f"Service returned status code {response.status_code}"}
        except Exception as e:
            health_status[service_name] = {"status": "error", "message": f"Service is not reachable: {e}"}
    
    # 整体状态
    all_ok = all(status["status"] == "ok" for status in health_status.values())
    overall_status = "ok" if all_ok else "error"
    
    return {
        "status": overall_status,
        "services": health_status
    }

# 代理到LLM服务
@app.get("/api/models")
async def get_models():
    """获取模型列表"""
    client = await http_client_manager.get_client(LLM_SERVICE_URL)
    response = await client.get("/api/models")
    if response.status_code == 200:
        return response.json()
    raise HTTPException(status_code=response.status_code, detail=response.text)

# 代理到记忆服务
@app.post("/api/memory")
async def add_memory(req: MemoryRequest):
    """添加记忆"""
    data = req.model_dump()
    
    # 通过消息队列发布消息
    try:
        message = {
            "type": "add_memory",
            "content": data.get("content"),
            "metadata": data.get("metadata")
        }
        message_queue_manager.publish("memory_queue", message)
        logger.info("通过消息队列发布添加记忆消息")
    except Exception as e:
        logger.warning(f"消息队列发布失败: {e}")
    
    # 同时通过HTTP请求添加记忆（作为备份）
    client = await http_client_manager.get_client(MEMORY_SERVICE_URL)
    response = await client.post("/api/memory", json=data)
    if response.status_code == 200:
        return response.json()
    raise HTTPException(status_code=response.status_code, detail=response.text)

@app.get("/api/memory/search")
async def search_memory(query: str, top_k: int = 5):
    """检索记忆"""
    client = await http_client_manager.get_client(MEMORY_SERVICE_URL)
    response = await client.get("/api/memory/search", params={"query": query, "top_k": top_k})
    if response.status_code == 200:
        return response.json()
    raise HTTPException(status_code=response.status_code, detail=response.text)

# 代理到认知服务
@app.post("/api/decision")
async def make_decision(request: Request):
    """做出决策"""
    data = await request.json()
    client = await http_client_manager.get_client(COGNITION_SERVICE_URL)
    response = await client.post("/api/decision", json=data)
    if response.status_code == 200:
        return response.json()
    raise HTTPException(status_code=response.status_code, detail=response.text)

# 代理到视觉服务
@app.post("/api/vision/classify")
async def classify_image(file: UploadFile = File(...)):
    """图像分类"""
    client = await http_client_manager.get_client(VISION_SERVICE_URL)
    files = {"file": (file.filename, await file.read(), file.content_type)}
    response = await client.post("/api/vision/classify", files=files)
    if response.status_code == 200:
        return response.json()
    raise HTTPException(status_code=response.status_code, detail=response.text)

@app.post("/api/vision/detect")
async def detect_objects(file: UploadFile = File(...)):
    """目标检测"""
    client = await http_client_manager.get_client(VISION_SERVICE_URL)
    files = {"file": (file.filename, await file.read(), file.content_type)}
    response = await client.post("/api/vision/detect", files=files)
    if response.status_code == 200:
        return response.json()
    raise HTTPException(status_code=response.status_code, detail=response.text)

@app.post("/api/vision/describe")
async def describe_image(file: UploadFile = File(...)):
    """图像描述"""
    client = await http_client_manager.get_client(VISION_SERVICE_URL)
    files = {"file": (file.filename, await file.read(), file.content_type)}
    response = await client.post("/api/vision/describe", files=files)
    if response.status_code == 200:
        return response.json()
    raise HTTPException(status_code=response.status_code, detail=response.text)

# 代理到多模态服务
@app.post("/api/multimodal/text")
async def process_text(request: Request):
    """处理文本输入"""
    form_data = await request.form()
    client = await http_client_manager.get_client(MULTIMODAL_SERVICE_URL)
    response = await client.post("/api/multimodal/text", data=form_data)
    if response.status_code == 200:
        return response.json()
    raise HTTPException(status_code=response.status_code, detail=response.text)

@app.post("/api/multimodal/image")
async def process_image(request: Request, file: UploadFile = File(...)):
    """处理图像输入"""
    form_data = await request.form()
    client = await http_client_manager.get_client(MULTIMODAL_SERVICE_URL)
    files = {"file": (file.filename, await file.read(), file.content_type)}
    response = await client.post("/api/multimodal/image", data=form_data, files=files)
    if response.status_code == 200:
        return response.json()
    raise HTTPException(status_code=response.status_code, detail=response.text)

@app.post("/api/multimodal/audio")
async def process_audio(request: Request, file: UploadFile = File(...)):
    """处理音频输入"""
    form_data = await request.form()
    client = await http_client_manager.get_client(MULTIMODAL_SERVICE_URL)
    files = {"file": (file.filename, await file.read(), file.content_type)}
    response = await client.post("/api/multimodal/audio", data=form_data, files=files)
    if response.status_code == 200:
        return response.json()
    raise HTTPException(status_code=response.status_code, detail=response.text)

@app.get("/api/multimodal/supported-input-types")
async def get_supported_input_types():
    """获取支持的输入类型"""
    client = await http_client_manager.get_client(MULTIMODAL_SERVICE_URL)
    response = await client.get("/api/multimodal/supported-input-types")
    if response.status_code == 200:
        return response.json()
    raise HTTPException(status_code=response.status_code, detail=response.text)

@app.get("/api/multimodal/supported-tasks")
async def get_supported_tasks():
    """获取支持的任务类型"""
    client = await http_client_manager.get_client(MULTIMODAL_SERVICE_URL)
    response = await client.get("/api/multimodal/supported-tasks")
    if response.status_code == 200:
        return response.json()
    raise HTTPException(status_code=response.status_code, detail=response.text)

# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Welcome to Bayesian-AGI-Core API Gateway",
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
        "src.api_gateway:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
