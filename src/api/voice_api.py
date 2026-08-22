#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语音处理API服务
提供HTTP和WebSocket语音处理接口

功能：
- HTTP端点：上传音频文件进行转录
- WebSocket端点：实时语音流处理
- 语音命令识别
- 多语言翻译
"""

import asyncio
import json
import logging
import base64
from typing import List, Dict, Any, Optional
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.core.multimodal.speech_processor import SpeechProcessor
from src.core.multimodal.audio_preprocessor import AudioPreprocessor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="Bayesian-AGI Speech Service",
    description="语音识别和处理服务",
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

# 创建处理器实例
speech_processor = SpeechProcessor(model_size="base")
audio_preprocessor = AudioPreprocessor()


class VoiceConnectionManager:
    """语音连接管理器

    管理所有WebSocket语音连接。
    """

    def __init__(self):
        """初始化连接管理器"""
        self.active_connections: List[WebSocket] = []
        self.connection_info: Dict[WebSocket, Dict] = {}

    async def connect(self, websocket: WebSocket, client_id: str = None):
        """接受新的WebSocket连接"""
        await websocket.accept()
        self.active_connections.append(websocket)

        self.connection_info[websocket] = {
            "client_id": client_id or f"client_{len(self.active_connections)}",
            "connected_at": asyncio.get_event_loop().time(),
            "audio_buffer": [],
            "language": "auto"
        }

        logger.info(
            f"New WebSocket connection: "
            f"{self.connection_info[websocket]['client_id']}"
        )

        # 发送欢迎消息
        await websocket.send_json({
            "type": "connected",
            "client_id": self.connection_info[websocket]["client_id"],
            "model_info": speech_processor.get_model_info()
        })

    def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

            client_id = self.connection_info.get(websocket, {}).get("client_id", "unknown")
            logger.info(f"WebSocket disconnected: {client_id}")

            if websocket in self.connection_info:
                del self.connection_info[websocket]

    async def broadcast(self, message: Dict):
        """广播消息到所有连接"""
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send to client: {e}")
                disconnected.append(connection)

        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)


# 全局连接管理器
voice_manager = VoiceConnectionManager()


# ============================================================
# WebSocket 端点
# ============================================================

@app.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    """WebSocket语音处理端点

    支持实时语音流处理。

    客户端发送的消息格式：
    {
        "type": "audio" | "config" | "transcribe",
        "data": "base64编码的音频数据",
        "language": "zh" | "en" | "auto",
        "task": "transcribe" | "translate"
    }

    服务端返回的消息格式：
    {
        "type": "result" | "error" | "config_ack",
        "text": "转录文本",
        "language": "检测到的语言",
        "confidence": 0.95,
        "duration": 2.5
    }
    """
    client_id = None

    try:
        await voice_manager.connect(websocket)
        client_id = voice_manager.connection_info[websocket]["client_id"]

        while True:
            # 接收消息
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "audio":
                # 处理音频数据
                await handle_audio_message(websocket, data)

            elif msg_type == "config":
                # 更新配置
                await handle_config_message(websocket, data)

            elif msg_type == "transcribe":
                # 触发转录
                await handle_transcribe_message(websocket, data)

            elif msg_type == "ping":
                # 心跳检测
                await websocket.send_json({"type": "pong"})

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}"
                })

    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")
        voice_manager.disconnect(websocket)

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
        voice_manager.disconnect(websocket)


async def handle_audio_message(websocket: WebSocket, data: Dict):
    """处理音频消息"""
    try:
        # 解码音频数据
        audio_base64 = data.get("data", "")
        audio_bytes = base64.b64decode(audio_base64)

        # 获取配置
        info = voice_manager.connection_info.get(websocket, {})
        language = data.get("language", info.get("language", "auto"))

        # 转录音频
        result = speech_processor.transcribe(
            audio_bytes,
            language=language,
            task="transcribe"
        )

        if "error" in result:
            await websocket.send_json({
                "type": "error",
                "message": result["error"]
            })
        else:
            await websocket.send_json({
                "type": "result",
                "text": result["text"],
                "language": result.get("language", "unknown"),
                "confidence": result.get("confidence", 0.0),
                "duration": result.get("duration", 0.0)
            })

    except Exception as e:
        logger.error(f"Audio processing error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"Audio processing failed: {str(e)}"
        })


async def handle_config_message(websocket: WebSocket, data: Dict):
    """处理配置消息"""
    info = voice_manager.connection_info.get(websocket, {})

    # 更新配置
    if "language" in data:
        info["language"] = data["language"]

    await websocket.send_json({
        "type": "config_ack",
        "language": info.get("language", "auto")
    })


async def handle_transcribe_message(websocket: WebSocket, data: Dict):
    """处理转录请求消息"""
    try:
        # 获取缓冲区中的所有音频
        info = voice_manager.connection_info.get(websocket, {})
        audio_buffer = info.get("audio_buffer", [])

        if not audio_buffer:
            await websocket.send_json({
                "type": "error",
                "message": "No audio data in buffer"
            })
            return

        # 合并所有音频块
        full_audio = b"".join(audio_buffer)

        # 获取参数
        language = data.get("language", info.get("language", "auto"))
        task = data.get("task", "transcribe")

        # 转录
        result = speech_processor.transcribe(
            full_audio,
            language=language,
            task=task
        )

        # 清空缓冲区
        info["audio_buffer"] = []

        if "error" in result:
            await websocket.send_json({
                "type": "error",
                "message": result["error"]
            })
        else:
            await websocket.send_json({
                "type": "result",
                "text": result["text"],
                "language": result.get("language", "unknown"),
                "confidence": result.get("confidence", 0.0),
                "duration": result.get("duration", 0.0),
                "segments": result.get("segments", [])
            })

    except Exception as e:
        logger.error(f"Transcribe error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"Transcription failed: {str(e)}"
        })


# ============================================================
# HTTP 端点
# ============================================================

@app.get("/")
async def root():
    """根端点"""
    return {
        "service": "Bayesian-AGI Speech Service",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "speech-service",
        "model_info": speech_processor.get_model_info()
    }


@app.get("/languages")
async def get_supported_languages():
    """获取支持的语言列表"""
    return {
        "languages": speech_processor.get_supported_languages()
    }


@app.get("/model-info")
async def get_model_info():
    """获取模型信息"""
    return speech_processor.get_model_info()


@app.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Form("auto"),
    task: str = Form("transcribe")
):
    """转录音频文件

    Args:
        file: 音频文件
        language: 语言代码（默认自动检测）
        task: 任务类型（transcribe或translate）

    Returns:
        转录结果
    """
    try:
        # 读取音频数据
        audio_data = await file.read()

        # 转录
        result = speech_processor.transcribe(
            audio_data,
            language=language,
            task=task
        )

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return {
            "success": True,
            "text": result["text"],
            "language": result.get("language", "unknown"),
            "confidence": result.get("confidence", 0.0),
            "duration": result.get("duration", 0.0)
        }

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/transcribe-base64")
async def transcribe_base64(
    audio_data: str = Form(...),
    language: str = Form("auto"),
    task: str = Form("transcribe")
):
    """转录Base64编码的音频数据

    Args:
        audio_data: Base64编码的音频数据
        language: 语言代码
        task: 任务类型

    Returns:
        转录结果
    """
    try:
        # 解码Base64
        audio_bytes = base64.b64decode(audio_data)

        # 转录
        result = speech_processor.transcribe(
            audio_bytes,
            language=language,
            task=task
        )

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return {
            "success": True,
            "text": result["text"],
            "language": result.get("language", "unknown"),
            "confidence": result.get("confidence", 0.0),
            "duration": result.get("duration", 0.0)
        }

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/detect-language")
async def detect_language(file: UploadFile = File(...)):
    """检测音频语言

    Args:
        file: 音频文件

    Returns:
        语言检测结果
    """
    try:
        audio_data = await file.read()

        result = speech_processor.detect_language(audio_data)

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return {
            "success": True,
            "language": result["language"],
            "language_name": result.get("language_name", "未知"),
            "confidence": result.get("confidence", 0.0)
        }

    except Exception as e:
        logger.error(f"Language detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recognize-command")
async def recognize_command(
    file: UploadFile = File(...),
    language: str = Form("zh")
):
    """识别语音命令

    Args:
        file: 音频文件
        language: 语言代码

    Returns:
        命令识别结果
    """
    try:
        audio_data = await file.read()

        # 预定义命令
        commands = {
            "启动": "start",
            "停止": "stop",
            "搜索": "search",
            "分析": "analyze",
            "打开": "open",
            "关闭": "close",
            "保存": "save",
            "删除": "delete"
        }

        result = speech_processor.recognize_commands(
            audio_data,
            commands,
            language=language
        )

        return {
            "success": True,
            "command": result["command"],
            "confidence": result.get("confidence", 0.0),
            "transcription": result.get("transcription", ""),
            "matched_keyword": result.get("matched_keyword")
        }

    except Exception as e:
        logger.error(f"Command recognition failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/preprocess")
async def preprocess_audio(
    file: UploadFile = File(...),
    remove_silence: bool = Form(False),
    normalize: bool = Form(True)
):
    """预处理音频

    Args:
        file: 音频文件
        remove_silence: 是否移除静音
        normalize: 是否归一化

    Returns:
        处理结果和特征
    """
    try:
        # 加载音频
        audio_data = await file.read()
        audio_np, sr = audio_preprocessor.load_audio(audio_bytes=audio_data)

        # 预处理
        if remove_silence:
            audio_np, _ = audio_preprocessor.remove_silence(audio_np)
        audio_np = audio_preprocessor.preprocess(audio_np, sr)

        # 提取特征
        features = audio_preprocessor.extract_features(audio_np, sr)

        return {
            "success": True,
            "duration": len(audio_np) / sr,
            "sample_rate": sr,
            "features": features
        }

    except Exception as e:
        logger.error(f"Audio preprocessing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 启动服务
# ============================================================

def start_server(host: str = "0.0.0.0", port: int = 8091):
    """启动语音服务

    Args:
        host: 监听地址
        port: 监听端口
    """
    logger.info("=" * 60)
    logger.info("Bayesian-AGI Speech Service 启动")
    logger.info("=" * 60)
    logger.info(f"服务地址: http://{host}:{port}")
    logger.info(f"WebSocket: ws://{host}:{port}/ws/voice")
    logger.info("")
    logger.info("可用端点:")
    logger.info("  - GET  /health           健康检查")
    logger.info("  - GET  /languages         支持的语言")
    logger.info("  - POST /transcribe         转录音频")
    logger.info("  - POST /detect-language   检测语言")
    logger.info("  - POST /recognize-command 识别命令")
    logger.info("  - WS   /ws/voice          实时语音处理")
    logger.info("=" * 60)

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    start_server()
