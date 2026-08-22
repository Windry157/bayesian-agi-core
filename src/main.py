#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI应用主入口
"""

import hashlib
import hmac
import time
import psutil
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Response, Body, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import json
import uuid
from datetime import datetime
from typing import Dict, Set
from pathlib import Path
from src.utils.config import load_config
from src.utils.assistant_singleton import get_assistant
from src.core.monitoring import monitoring

# 导入健壮性功能
from src.utils.structured_logging import get_logger, get_trace_id, new_trace_id, set_trace_id
from src.utils.circuit_breaker import CircuitBreakerManager, get_circuit_breaker
from src.utils.rate_limiter import RateLimiterManager, get_rate_limiter_manager

# 使用结构化日志
logger = get_logger("main")

# 使用单例获取智能助理实例
assistant = get_assistant()

# 在模块顶部加载并缓存 websocket 配置，避免每次请求都加载
_cached_websocket_config = None
def _get_websocket_config():
    """获取缓存的 websocket 配置"""
    global _cached_websocket_config
    if _cached_websocket_config is None:
        config = load_config()
        _cached_websocket_config = config.get("websocket", {})
    return _cached_websocket_config


# Lifespan 事件处理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动事件
    trace_id = new_trace_id()
    logger.info("开始启动智能助理...", trace_id=trace_id)
    config = load_config()
    logger.info(f"加载的配置: {config}")
    await assistant.initialize(config)

    # 初始化全局文本生成器
    models_config = config.get("models", {})
    ollama_url = models_config.get("ollama_url", "http://192.168.3.105:11434")
    default_model = models_config.get("default", "gemma4:e4b")
    logger.info(f"使用配置的模型: {default_model} at {ollama_url}")
    
    try:
        from src.core.uncertainty.text_generator import initialize_text_generator
        initialize_text_generator(ollama_url=ollama_url, default_model=default_model)
        logger.info(f"全局文本生成器初始化完成: {default_model}")
    except Exception as e:
        logger.error(f"文本生成器初始化失败: {e}")

    # 自检嵌入模型 — 缺失自动拉取
    try:
        from src.utils.model_bootstrap import ensure_models
        memory_config = config.get("memory", {})
        embed_model = memory_config.get("vector_model", "nomic-embed-text")
        await ensure_models(ollama_url, default_model, embed_model)
    except Exception as e:
        logger.warning(f"模型自检跳过: {e}")

    # 注册Ollama服务
    try:
        from src.core.llm.ollama_service import OllamaLLM

        ollama_config = config.get("models", {})
        if ollama_config:
            llm_service = OllamaLLM(ollama_config)
            assistant.register_service("llm", llm_service)
            logger.info("Ollama LLM 服务注册成功")
    except Exception as e:
        logger.error(f"LLM 服务注册失败: {e}")

    # 初始化健壮性功能
    rate_limiter_mgr = get_rate_limiter_manager()
    # 注册常用限流器
    rate_limiter_mgr.register_limiter(
        'api_global', 'sliding_window', requests=1000, period_seconds=60
    )
    rate_limiter_mgr.register_limiter(
        'per_user', 'token_bucket', requests=60, period_seconds=60, burst_size=20
    )
    logger.info("Rate limiters initialized")

    # 注册熔断器
    get_circuit_breaker('ollama_service', failure_threshold=3, recovery_timeout=30)
    get_circuit_breaker('llm_generation', failure_threshold=5, recovery_timeout=60)
    logger.info("Circuit breakers initialized")

    yield

    # 关闭事件（如果需要）
    logger.info("智能助理关闭")


# 导入 Bridge Server
from src.core.bridge import get_bridge_server, BridgeConfig

# 创建FastAPI应用
app = FastAPI(
    title="Bayesian-AGI-Core",
    description="基于自由能原理和主动推理的认知智能体",
    version="1.0.0",
    lifespan=lifespan,
)

# 挂载 Bridge Server 代理 (OpenClaw 兼容)
# 监听 /bridge/* 路径，避免与主应用冲突
bridge_app = get_bridge_server().app
app.mount("/bridge", bridge_app, name="bridge")

# 挂载静态文件目录
static_dir = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# 添加 UI 路由
@app.get("/ui", response_class=FileResponse)
def ui():
    """交互界面"""
    return FileResponse(static_dir / "index.html")

@app.get("/docs", response_class=FileResponse)
def docs():
    """API 文档页面"""
    return FileResponse(static_dir / "api_docs.html")


# 配置CORS
# 从环境变量或配置中读取允许的来源
_env = os.getenv("APP_ENV", "development")
_cors_origins = os.getenv("CORS_ORIGINS", "")
if _cors_origins:
    allowed_origins = [o.strip() for o in _cors_origins.split(",") if o.strip()]
elif _env == "production":
    # 生产环境：默认只允许本地域
    allowed_origins = ["http://localhost", "http://127.0.0.1"]
else:
    # 开发环境：允许更多来源
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加监控中间件
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """监控中间件：记录所有HTTP请求的指标"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    # 记录请求
    monitoring.record_request(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code,
        duration=process_time
    )

    # 记录系统资源使用情况
    monitoring.record_memory_usage(psutil.virtual_memory().used)
    monitoring.record_cpu_usage(psutil.cpu_percent())

    return response


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
async def add_memory(content: str = Body(...), metadata: dict = None):
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
async def make_decision(possible_actions: list = Body(...)):
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
        "docs": "/docs",
    }


# Prometheus指标端点
@app.get("/health/metrics")
def metrics():
    """Prometheus指标端点：返回真实的监控数据"""
    try:
        from src.core.observability import init_observability
        observability = init_observability()
        content = observability.export_prometheus_metrics()
        from fastapi.responses import Response
        return Response(content=content, media_type="text/plain; version=0.0.4")
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        from fastapi.responses import Response
        return Response(content=f"Error: {str(e)}", status_code=500)


# 仪表盘数据端点
@app.get("/api/dashboard")
def dashboard():
    """获取系统仪表盘数据"""
    try:
        from src.core.observability import init_observability
        observability = init_observability()
        return observability.get_dashboard_data()
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard data: {e}")


# 健康检查详情端点
@app.get("/health/detailed")
def health_detailed():
    """获取详细健康检查信息"""
    try:
        from src.core.observability import init_observability
        observability = init_observability()
        return observability.check_health()
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}")


# 仪表盘页面
@app.get("/dashboard")
def dashboard_page():
    """监控仪表盘页面"""
    return FileResponse("static/dashboard.html")


# 注册 API 路由
try:
    from src.api.security_api import router as security_router
    app.include_router(security_router)
    logger.info("安全服务 API 路由注册成功")
except Exception as e:
    logger.error(f"安全服务 API 路由注册失败: {e}")

try:
    from src.api.observability_api import router as observability_router
    app.include_router(observability_router)
    logger.info("可观测性服务 API 路由注册成功")
except Exception as e:
    logger.error(f"可观测性服务 API 路由注册失败: {e}")

try:
    from src.api.self_healing_api import router as self_healing_router
    app.include_router(self_healing_router)
    logger.info("自愈服务 API 路由注册成功")
except Exception as e:
    logger.error(f"自愈服务 API 路由注册失败: {e}")


# =============================================================================
# WebSocket 服务（兼容 OpenClaw 协议）
# =============================================================================

# WebSocket 连接管理
active_connections: Set[WebSocket] = set()
connection_info: Dict[str, Dict] = {}

def generate_challenge_nonce() -> str:
    """生成挑战随机数"""
    return uuid.uuid4().hex

def verify_challenge_response(nonce: str, response: str) -> bool:
    """
    使用 HMAC-SHA256 验证挑战响应
    
    响应必须是 HMAC-SHA256(nonce, secret_key) 的十六进制格式
    """
    websocket_config = _get_websocket_config()
    secret_key = websocket_config.get("auth_secret", "CHANGE_ME_IN_PRODUCTION")

    expected = hmac.new(
        secret_key.encode('utf-8'),
        nonce.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(response, expected)

async def websocket_handler(websocket: WebSocket):
    """处理 WebSocket 连接"""
    await websocket.accept()
    connection_id = str(uuid.uuid4())
    active_connections.add(websocket)
    
    connection_info[connection_id] = {
        "connected_at": datetime.now().isoformat(),
        "status": "connected",
        "client_type": "unknown"
    }
    
    try:
        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                break
            
            msg_type = data.get("type", "")
            
            if msg_type == "connect":
                challenge = generate_challenge_nonce()
                await websocket.send_json({
                    "type": "challenge",
                    "nonce": challenge
                })
            
            elif msg_type == "challenge-response":
                nonce = data.get("nonce", "")
                response = data.get("response", "")
                
                if verify_challenge_response(nonce, response):
                    await websocket.send_json({
                        "type": "connected",
                        "success": True,
                        "message": "Handshake successful"
                    })
                    connection_info[connection_id]["status"] = "authenticated"
                    connection_info[connection_id]["client_type"] = data.get("client", "unknown")
                    logger.info(f"WebSocket client authenticated: {connection_info[connection_id]['client_type']}")
                else:
                    await websocket.send_json({
                        "type": "error",
                        "code": 401,
                        "message": "Invalid challenge response"
                    })
                    break
            
            elif msg_type == "message":
                session_id = data.get("session_id", "default")
                content = data.get("content", "")
                model = data.get("model", None)

                if not content:
                    await websocket.send_json({
                        "type": "error",
                        "code": 400,
                        "message": "Empty message content"
                    })
                    continue

                try:
                    async for event in assistant.process_with_context_stream(content, session_id, model=model):
                        await websocket.send_json({
                            "type": event.get("type", "unknown"),
                            "session_id": session_id,
                            "content": event.get("content", ""),
                            "tool": event.get("tool", ""),
                            "args": event.get("args"),
                            "output": event.get("output"),
                            "tool_rounds": event.get("tool_rounds", []),
                            "tool_count": event.get("tool_count", 0),
                            "model": event.get("model", model or assistant.get_active_model()),
                            "timestamp": datetime.now().isoformat()
                        })
                except Exception as e:
                    logger.error(f"Message processing failed: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "code": 500,
                        "message": str(e)
                    })

            elif msg_type == "tool-call":
                tool_name = data.get("tool", "")
                params = data.get("params", {})

                if not tool_name:
                    await websocket.send_json({
                        "type": "error",
                        "code": 400,
                        "message": "Missing tool name"
                    })
                    continue

                try:
                    result = await assistant.execute_tool(tool_name, params)
                    await websocket.send_json({
                        "type": "tool-result",
                        "tool": tool_name,
                        "result": result,
                        "timestamp": datetime.now().isoformat()
                    })
                except Exception as e:
                    logger.error(f"Tool execution failed: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "code": 500,
                        "message": str(e)
                    })

            elif msg_type == "tools-list":
                await websocket.send_json({
                    "type": "tools-list-response",
                    "tools": assistant.list_tools(),
                    "timestamp": datetime.now().isoformat()
                })

            elif msg_type == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })

            else:
                await websocket.send_json({
                    "type": "error",
                    "code": 400,
                    "message": f"Unknown message type: {msg_type}"
                })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket connection closed: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        active_connections.discard(websocket)
        connection_info.pop(connection_id, None)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 端点"""
    await websocket_handler(websocket)

@app.websocket("/api/v1/ws")
async def websocket_v1_endpoint(websocket: WebSocket):
    """WebSocket v1 端点"""
    await websocket_handler(websocket)

@app.get("/api/ws/connections")
async def get_ws_connections():
    """获取当前 WebSocket 连接状态"""
    return {
        "active_connections": len(active_connections),
        "connections": list(connection_info.values())
    }


# =============================================================================
# 微信消息通道
# =============================================================================

@app.post("/api/wechat/webhook")
async def wechat_webhook(request: Request):
    """微信消息 Webhook"""
    try:
        cfg = load_config()
        wechat = cfg.get("wechat", {})
        
        if not wechat.get("enabled", False):
            return {"code": -1, "msg": "wechat not enabled"}
        
        body = await request.body()
        data = json.loads(body.decode("utf-8"))
        
        msg_type = data.get("MsgType", "")
        content = ""
        user_id = data.get("FromUserName", "")
        
        if msg_type == "text":
            content = data.get("Content", "").strip()
        elif msg_type == "image":
            return {"code": 0, "msg": "暂不支持图片消息"}
        elif msg_type == "voice":
            return {"code": 0, "msg": "暂不支持语音消息"}
        else:
            return {"code": 0, "msg": f"暂不支持消息类型: {msg_type}"}
        
        if not content:
            return {"code": 0}
        
        result = await assistant.process_with_context(content, f"wechat-{user_id}")
        response_text = result.get("response", "")
        
        return {
            "code": 0,
            "msg": "success",
            "response": response_text[:2000]
        }
    
    except Exception as e:
        logger.error(f"WeChat webhook error: {e}")
        return {"code": -1, "msg": str(e)}


# =============================================================================
# 健壮性管理 API
# =============================================================================

@app.get("/api/circuit-breakers", tags=["robustness"])
async def list_circuit_breakers():
    """列出所有熔断器状态"""
    circuits = CircuitBreakerManager.list_circuits()
    return {
        "status": "success",
        "data": circuits
    }


@app.post("/api/circuit-breakers/{name}/reset", tags=["robustness"])
async def reset_circuit_breaker(name: str):
    """重置指定熔断器"""
    CircuitBreakerManager.reset_circuit(name)
    return {
        "status": "success",
        "message": f"Circuit breaker '{name}' reset"
    }


@app.post("/api/circuit-breakers/reset-all", tags=["robustness"])
async def reset_all_circuit_breakers():
    """重置所有熔断器"""
    CircuitBreakerManager.reset_all()
    return {
        "status": "success",
        "message": "All circuit breakers reset"
    }


@app.get("/api/rate-limiters", tags=["robustness"])
async def list_rate_limiters():
    """列出所有限流器"""
    manager = get_rate_limiter_manager()
    limiters = manager.list_limiters()
    return {
        "status": "success",
        "data": limiters
    }


@app.get("/api/rate-limiters/{name}/stats", tags=["robustness"])
async def get_rate_limiter_stats(name: str, key: str = "default"):
    """获取指定限流器的统计信息"""
    manager = get_rate_limiter_manager()
    stats = manager.get_stats(name, key)
    if stats is None:
        raise HTTPException(status_code=404, detail=f"Rate limiter '{name}' not found")
    return {
        "status": "success",
        "data": stats
    }


@app.get("/api/health/robustness", tags=["robustness"])
async def get_robustness_health():
    """获取健壮性系统健康状态"""
    manager = get_rate_limiter_manager()
    circuits = CircuitBreakerManager.list_circuits()
    limiters = manager.list_limiters()
    
    total_circuits = len(circuits)
    open_circuits = sum(1 for c in circuits.values() if c['state'] == 'open')
    
    health_status = "healthy"
    if open_circuits > 0:
        health_status = "degraded"
    
    return {
        "status": health_status,
        "circuit_breakers": {
            "total": total_circuits,
            "open": open_circuits,
            "closed": total_circuits - open_circuits,
            "details": circuits
        },
        "rate_limiters": {
            "total": len(limiters),
            "details": limiters
        }
    }


# =============================================================================
# Coding Tools API
# =============================================================================

@app.get("/api/tools", tags=["tools"])
async def list_tools():
    return {"tools": assistant.list_tools()}


@app.post("/api/tools/{tool_name}", tags=["tools"])
async def execute_tool(tool_name: str, params: dict = Body(...)):
    result = await assistant.execute_tool(tool_name, params)
    return result


# =============================================================================
# 动态模型管理 API
# =============================================================================

@app.get("/api/models/live", tags=["models"])
async def list_models_live():
    models = await assistant.refresh_models()
    return {
        "models": models,
        "active": assistant.get_active_model(),
    }


@app.post("/api/models/refresh", tags=["models"])
async def refresh_models():
    models = await assistant.refresh_models()
    return {"models": models, "count": len(models)}


@app.get("/api/models/active", tags=["models"])
async def get_active_model():
    return {"active": assistant.get_active_model()}


@app.post("/api/models/switch", tags=["models"])
async def switch_model(data: dict = Body(...)):
    model_name = data.get("model", "")
    if not model_name:
        raise HTTPException(status_code=400, detail="Missing model name")
    if assistant.switch_model(model_name):
        return {"active": model_name, "message": f"已切换为 {model_name}"}
    raise HTTPException(status_code=404, detail=f"模型 {model_name} 不可用")


# 中间件：为每个请求添加trace_id
@app.middleware("http")
async def add_trace_id(request: Request, call_next):
    """为每个请求添加追踪ID"""
    trace_id = request.headers.get("X-Trace-ID", new_trace_id())
    set_trace_id(trace_id)
    
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    
    response.headers["X-Trace-ID"] = trace_id
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
    
    return response


# 异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.exception(
        f"Unhandled exception for {request.method} {request.url}",
        exception_type=type(exc).__name__,
        exception=str(exc)
    )
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "code": 500,
            "message": "Internal server error",
            "trace_id": get_trace_id()
        }
    )


if __name__ == "__main__":
    import uvicorn

    config = load_config()
    server_config = config.get("server", {})
    host = server_config.get("host", "0.0.0.0")
    port = server_config.get("port", 8000)
    workers = server_config.get("workers", 4)

    reload_enabled = os.getenv("APP_ENV", "development") != "production"
    uvicorn.run("src.main:app", host=host, port=port, workers=workers, reload=reload_enabled)
