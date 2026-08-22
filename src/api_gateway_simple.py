#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版 API Gateway
专注于核心聊天和Web界面功能
"""

import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="Bayesian-AGI-Core API Gateway",
    description="API Gateway for Bayesian-AGI-Core - Simplified Version",
    version="1.0.0",
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# 定义请求模型
class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    session_id: str = "default"
    enable_context: bool = True


class ChatResponse(BaseModel):
    """聊天响应模型"""
    response: str
    confidence: float
    confidence_level: str
    confidence_range: Dict[str, float]
    uncertainty_sources: list
    session_id: str
    timestamp: str


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "message": "API Gateway is running"}


# 聊天接口 - 带置信度评估
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """聊天接口，带置信度评估"""
    try:
        from src.core.assistant import Assistant

        assistant = Assistant()

        # 处理上下文
        if request.enable_context:
            result = await assistant.process_with_context(request.message, request.session_id)
        else:
            result = {"response": f"简洁回答: {request.message}", "context_used": False}

        response_text = result.get("response", "抱歉，我无法处理这个请求。")

        # 置信度评估
        confidence_score = result.get("confidence_score", 0.75)
        confidence_level = result.get("confidence_level", "medium")

        if confidence_score >= 0.8:
            confidence_level = "high"
        elif confidence_score >= 0.6:
            confidence_level = "medium"
        elif confidence_score >= 0.4:
            confidence_level = "low"
        else:
            confidence_level = "very_low"

        return ChatResponse(
            response=response_text,
            confidence=confidence_score,
            confidence_level=confidence_level,
            confidence_range={
                "lower": max(0.0, confidence_score - 0.1),
                "upper": min(1.0, confidence_score + 0.1)
            },
            uncertainty_sources=result.get("uncertainty_sources", []),
            session_id=request.session_id,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"聊天处理失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {e}")


# 根路径
@app.get("/")
async def root():
    """根路径 - 返回Web界面"""
    static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    index_path = os.path.join(static_path, "index.html")
    logger.info(f"Static path: {static_path}")
    logger.info(f"Index path: {index_path}")
    logger.info(f"File exists: {os.path.exists(index_path)}")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": "Welcome to Bayesian-AGI-Core API Gateway",
        "version": "1.0.0",
        "docs": "/docs",
    }


# 挂载静态文件
static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api_gateway_simple:app", host="0.0.0.0", port=8080, reload=True)
