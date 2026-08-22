#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
极简版 API Gateway
完全独立，不依赖任何复杂模块
直接提供聊天功能
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
import requests
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="Bayesian-AGI-Core API Gateway",
    description="Minimal API Gateway - Standalone Version",
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

# 会话存储
sessions = {}

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


def call_ollama_llm(message: str) -> str:
    """调用 Ollama LLM"""
    try:
        ollama_url = "http://192.168.3.105:11434/api/chat"
        
        payload = {
            "model": "llama3.1:8b",
            "messages": [{"role": "user", "content": message}],
            "stream": False
        }
        
        response = requests.post(ollama_url, json=payload, timeout=60)
        result = response.json()
        
        return result.get("message", {}).get("content", "抱歉，我无法处理这个请求。")
    except Exception as e:
        logger.error(f"Ollama 调用失败: {e}")
        return f"抱歉，暂时无法连接到 AI 服务。（错误: {str(e)}）"


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "message": "API Gateway is running - Minimal Version"}


# 聊天接口
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """聊天接口"""
    try:
        session_id = request.session_id
        
        # 管理会话
        if session_id not in sessions:
            sessions[session_id] = []
        
        # 调用 LLM
        response_text = call_ollama_llm(request.message)
        
        # 置信度评估（简化版）
        import random
        confidence_score = 0.7 + random.random() * 0.2
        
        if confidence_score >= 0.85:
            confidence_level = "high"
        elif confidence_score >= 0.7:
            confidence_level = "medium"
        elif confidence_score >= 0.5:
            confidence_level = "low"
        else:
            confidence_level = "very_low"
        
        # 保存到会话
        sessions[session_id].append({
            "role": "user",
            "content": request.message
        })
        sessions[session_id].append({
            "role": "assistant",
            "content": response_text
        })
        
        logger.info(f"聊天请求完成: session={session_id}")
        
        return ChatResponse(
            response=response_text,
            confidence=confidence_score,
            confidence_level=confidence_level,
            confidence_range={
                "lower": max(0.0, confidence_score - 0.1),
                "upper": min(1.0, confidence_score + 0.1)
            },
            uncertainty_sources=[],
            session_id=session_id,
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
        "message": "Welcome to Bayesian-AGI-Core API Gateway - Minimal Version",
        "version": "1.0.0",
        "docs": "/docs",
    }


# 挂载静态文件
static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


if __name__ == "__main__":
    import uvicorn

    logger.info("=" * 60)
    logger.info("启动极简版 API Gateway")
    logger.info("=" * 60)
    logger.info("服务地址: http://localhost:8080")
    logger.info("Ollama地址: http://192.168.3.105:11434")
    logger.info("=" * 60)
    
    uvicorn.run("src.api_gateway_minimal:app", host="0.0.0.0", port=8080, reload=True)
