#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multimodal Service
处理多模态输入
"""

import os
import logging
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from src.core.multimodal.multimodal_processor import BasicMultimodalProcessor
from src.core.monitoring import monitoring

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="Bayesian-AGI-Core Multimodal Service",
    description="Multimodal Service for Bayesian-AGI-Core",
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

# 创建多模态处理器
multimodal_processor = BasicMultimodalProcessor()


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "message": "Multimodal Service is running"}


# 处理文本输入
@app.post("/api/multimodal/text")
async def process_text(text: str = Form(...), task: str = Form(...)):
    """处理文本输入"""
    try:
        result = multimodal_processor.process(text, "text", task)
        logger.info(f"文本处理结果: {result}")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process text: {e}")


# 处理图像输入
@app.post("/api/multimodal/image")
async def process_image(file: UploadFile = File(...), task: str = Form(...)):
    """处理图像输入"""
    try:
        # 读取图像
        image = Image.open(file.file)
        # 处理图像
        result = multimodal_processor.process(image, "image", task)
        logger.info(f"图像处理结果: {result}")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process image: {e}")


# 处理音频输入
@app.post("/api/multimodal/audio")
async def process_audio(file: UploadFile = File(...), task: str = Form(...)):
    """处理音频输入"""
    try:
        # 读取音频
        audio = await file.read()
        # 处理音频
        result = multimodal_processor.process(audio, "audio", task)
        logger.info(f"音频处理结果: {result}")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process audio: {e}")


# 获取支持的输入类型
@app.get("/api/multimodal/supported-input-types")
async def get_supported_input_types():
    """获取支持的输入类型"""
    return {"input_types": multimodal_processor.get_supported_input_types()}


# 获取支持的任务类型
@app.get("/api/multimodal/supported-tasks")
async def get_supported_tasks():
    """获取支持的任务类型"""
    return {"tasks": multimodal_processor.get_supported_tasks()}


# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Welcome to Bayesian-AGI-Core Multimodal Service",
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

    uvicorn.run("src.multimodal_service", host="0.0.0.0", port=8005, reload=True)
