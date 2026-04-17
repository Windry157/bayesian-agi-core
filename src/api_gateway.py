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
from src.utils.high_availability import high_availability_manager
from src.utils.service_discovery import service_discovery
from src.utils.service_mesh import service_mesh
from src.utils.auto_scaling import auto_scaling_manager
from src.utils.multi_region import multi_region_manager
from src.core.monitoring import monitoring
from src.services import monitoring_service
from src.core.consciousness import consciousness
from src.core.uncertainty import feedback_collector

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="Bayesian-AGI-Core API Gateway",
    description="API Gateway for Bayesian-AGI-Core microservices",
    version="1.0.0",
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


class ConsciousnessRequest(BaseModel):
    input: str
    session_id: str = "default"
    enable_continuous_thought: bool = True


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
    
    # 注册服务实例
    services = {
        "llm_service": LLM_SERVICE_URL,
        "memory_service": MEMORY_SERVICE_URL,
        "cognition_service": COGNITION_SERVICE_URL,
        "vision_service": VISION_SERVICE_URL,
        "multimodal_service": MULTIMODAL_SERVICE_URL
    }
    
    for service_name, service_url in services.items():
        # 注册到服务发现
        service_discovery.register_service(service_name, service_url)
        # 注册到服务网格
        service_mesh.register_service(service_name, {
            "url": service_url,
            "type": "http",
            "version": "1.0",
            "endpoints": ["/health", "/api"]
        })
    
    # 启动高可用管理器
    await high_availability_manager.start()
    
    # 启动监控服务
    await monitoring_service.start()
    
    # 初始化意识系统
    try:
        await consciousness.initialize()
        logger.info("意识系统初始化成功")
    except Exception as e:
        logger.error(f"意识系统初始化失败: {e}")
        # 继续启动，意识系统可能不是关键依赖
    
    # 为服务设置扩缩容配置
    services = ["llm_service", "memory_service", "cognition_service", "vision_service", "multimodal_service"]
    for service in services:
        auto_scaling_manager.set_scaling_config(service, {
            "min_instances": 1,
            "max_instances": 3,
            "target_load": 0.6,
            "scale_up_threshold": 0.8,
            "scale_down_threshold": 0.4
        })
    
    # 启动自动扩缩容管理器
    await auto_scaling_manager.start()
    
    # 初始化多区域部署
    # 添加区域
    multi_region_manager.add_region("region-1", {
        "name": "Region 1",
        "location": "us-east-1",
        "priority": 1
    })
    
    multi_region_manager.add_region("region-2", {
        "name": "Region 2",
        "location": "us-west-1",
        "priority": 2
    })
    
    multi_region_manager.add_region("region-3", {
        "name": "Region 3",
        "location": "eu-west-1",
        "priority": 3
    })
    
    # 为每个区域添加服务实例
    services = ["llm_service", "memory_service", "cognition_service", "vision_service", "multimodal_service"]
    base_urls = {
        "region-1": "http://localhost:8001",
        "region-2": "http://localhost:8002",
        "region-3": "http://localhost:8003"
    }
    
    for region_id, base_url in base_urls.items():
        for service_name in services:
            # 为每个服务添加实例
            instance_url = f"{base_url}/{service_name}"
            multi_region_manager.add_service_instance(region_id, service_name, instance_url)
    
    # 添加路由规则
    multi_region_manager.add_routing_rule({
        "name": "us-east-1-rule",
        "service": "llm_service",
        "region": "region-1",
        "location": "us-east"
    })
    
    multi_region_manager.add_routing_rule({
        "name": "us-west-1-rule",
        "service": "memory_service",
        "region": "region-2",
        "location": "us-west"
    })
    
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
        "multimodal_service": MULTIMODAL_SERVICE_URL,
    }

    health_status = {}
    for service_name, service_url in services.items():
        try:
            client = await http_client_manager.get_client(service_url)
            response = await client.get("/health")
            if response.status_code == 200:
                health_status[service_name] = {
                    "status": "ok",
                    "message": "Service is running",
                }
            else:
                health_status[service_name] = {
                    "status": "error",
                    "message": f"Service returned status code {response.status_code}",
                }
        except Exception as e:
            health_status[service_name] = {
                "status": "error",
                "message": f"Service is not reachable: {e}",
            }

    # 整体状态
    all_ok = all(status["status"] == "ok" for status in health_status.values())
    overall_status = "ok" if all_ok else "error"

    return {"status": overall_status, "services": health_status}


# 代理到LLM服务
@app.get("/api/models")
async def get_models():
    """获取模型列表"""
    try:
        response = await high_availability_manager.execute_with_failover(
            "llm_service", "GET", "/api/models"
        )
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Service call failed: {e}")


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
            "metadata": data.get("metadata"),
        }
        message_queue_manager.publish("memory_queue", message)
        logger.info("通过消息队列发布添加记忆消息")
    except Exception as e:
        logger.warning(f"消息队列发布失败: {e}")

    # 同时通过HTTP请求添加记忆（作为备份）
    try:
        response = await high_availability_manager.execute_with_failover(
            "memory_service", "POST", "/api/memory", json=data
        )
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Service call failed: {e}")


@app.get("/api/memory/search")
async def search_memory(query: str, top_k: int = 5):
    """检索记忆"""
    try:
        response = await high_availability_manager.execute_with_failover(
            "memory_service", "GET", "/api/memory/search", params={"query": query, "top_k": top_k}
        )
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Service call failed: {e}")


# 代理到认知服务
@app.post("/api/decision")
async def make_decision(request: Request):
    """做出决策"""
    data = await request.json()
    try:
        response = await high_availability_manager.execute_with_failover(
            "cognition_service", "POST", "/api/decision", json=data
        )
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Service call failed: {e}")

# 持续上下文处理
@app.post("/api/context/process")
async def process_with_context(request: Request):
    """基于持续上下文处理请求"""
    data = await request.json()
    input_text = data.get("input")
    session_id = data.get("session_id")
    
    if not input_text or not session_id:
        raise HTTPException(status_code=400, detail="Missing input or session_id")
    
    try:
        # 从assistant实例获取处理结果
        from src.core.assistant import Assistant
        assistant = Assistant()
        result = await assistant.process_with_context(input_text, session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Process failed: {e}")

# 自我完善循环
@app.post("/api/self-improvement")
async def self_improvement():
    """触发自我完善循环"""
    try:
        from src.core.assistant import Assistant
        assistant = Assistant()
        result = await assistant.self_improvement_cycle()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Self improvement failed: {e}")

# 生成学习目标
@app.get("/api/learning/goals")
async def generate_learning_goals():
    """生成学习目标"""
    try:
        from src.core.assistant import Assistant
        assistant = Assistant()
        goals = await assistant.generate_learning_goals()
        return {"goals": goals}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Goal generation failed: {e}")

# 启动自主学习
@app.post("/api/learning/start")
async def start_autonomous_learning():
    """启动自主学习"""
    try:
        from src.core.assistant import Assistant
        assistant = Assistant()
        success = await assistant.start_autonomous_learning()
        return {"success": success, "message": "Autonomous learning started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start learning: {e}")

# 获取系统健康状态
@app.get("/api/system/health")
async def get_system_health():
    """获取系统健康状态"""
    try:
        from src.core.assistant import Assistant
        assistant = Assistant()
        health = assistant.get_system_health()
        return health
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}")


# 意识系统端点
@app.post("/api/consciousness/process")
async def process_consciousness(req: ConsciousnessRequest):
    """处理连续思维"""
    try:
        result = await consciousness.process_thought(
            input_text=req.input,
            session_id=req.session_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Consciousness processing failed: {e}")


@app.get("/api/consciousness/status")
async def get_consciousness_status():
    """获取意识状态"""
    try:
        status = consciousness.get_consciousness_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get consciousness status: {e}")


@app.post("/api/consciousness/evolve")
async def trigger_consciousness_evolution():
    """触发意识进化"""
    try:
        # 执行进化逻辑
        await consciousness._evolve_and_learn({}, {"confidence": 0.5})
        return {"success": True, "message": "Consciousness evolution triggered"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evolution failed: {e}")


@app.post("/api/consciousness/learn")
async def start_consciousness_learning():
    """启动意识学习"""
    try:
        # 执行学习逻辑
        await consciousness._initiate_active_learning(["主动学习启动"])
        return {"success": True, "message": "Consciousness learning started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Learning failed: {e}")


# 代理到视觉服务
@app.post("/api/vision/classify")
async def classify_image(file: UploadFile = File(...)):
    """图像分类"""
    try:
        files = {"file": (file.filename, await file.read(), file.content_type)}
        response = await high_availability_manager.execute_with_failover(
            "vision_service", "POST", "/api/vision/classify", files=files
        )
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Service call failed: {e}")


@app.post("/api/vision/detect")
async def detect_objects(file: UploadFile = File(...)):
    """目标检测"""
    try:
        files = {"file": (file.filename, await file.read(), file.content_type)}
        response = await high_availability_manager.execute_with_failover(
            "vision_service", "POST", "/api/vision/detect", files=files
        )
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Service call failed: {e}")


@app.post("/api/vision/describe")
async def describe_image(file: UploadFile = File(...)):
    """图像描述"""
    try:
        files = {"file": (file.filename, await file.read(), file.content_type)}
        response = await high_availability_manager.execute_with_failover(
            "vision_service", "POST", "/api/vision/describe", files=files
        )
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Service call failed: {e}")


# 代理到多模态服务
@app.post("/api/multimodal/text")
async def process_text(request: Request):
    """处理文本输入"""
    try:
        form_data = await request.form()
        response = await high_availability_manager.execute_with_failover(
            "multimodal_service", "POST", "/api/multimodal/text", data=form_data
        )
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Service call failed: {e}")


@app.post("/api/multimodal/image")
async def process_image(request: Request, file: UploadFile = File(...)):
    """处理图像输入"""
    try:
        form_data = await request.form()
        files = {"file": (file.filename, await file.read(), file.content_type)}
        response = await high_availability_manager.execute_with_failover(
            "multimodal_service", "POST", "/api/multimodal/image", data=form_data, files=files
        )
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Service call failed: {e}")


@app.post("/api/multimodal/audio")
async def process_audio(request: Request, file: UploadFile = File(...)):
    """处理音频输入"""
    try:
        form_data = await request.form()
        files = {"file": (file.filename, await file.read(), file.content_type)}
        response = await high_availability_manager.execute_with_failover(
            "multimodal_service", "POST", "/api/multimodal/audio", data=form_data, files=files
        )
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Service call failed: {e}")


@app.get("/api/multimodal/supported-input-types")
async def get_supported_input_types():
    """获取支持的输入类型"""
    try:
        response = await high_availability_manager.execute_with_failover(
            "multimodal_service", "GET", "/api/multimodal/supported-input-types"
        )
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Service call failed: {e}")


@app.get("/api/multimodal/supported-tasks")
async def get_supported_tasks():
    """获取支持的任务类型"""
    try:
        response = await high_availability_manager.execute_with_failover(
            "multimodal_service", "GET", "/api/multimodal/supported-tasks"
        )
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Service call failed: {e}")


# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Welcome to Bayesian-AGI-Core API Gateway",
        "version": "1.0.0",
        "docs": "/docs",
    }


# 系统状态端点
@app.get("/api/monitoring/system-status")
async def get_system_status():
    """获取系统状态"""
    try:
        status = await monitoring_service.get_system_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system status: {e}")

# 服务健康状态端点
@app.get("/api/monitoring/service-health")
async def get_service_health():
    """获取服务健康状态"""
    try:
        availability = high_availability_manager.get_service_availability()
        return availability
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get service health: {e}")

# 服务网格状态端点
@app.get("/api/service-mesh/status")
async def get_service_mesh_status():
    """获取服务网格状态"""
    try:
        status = service_mesh.get_service_mesh_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get service mesh status: {e}")

# 服务网格服务列表端点
@app.get("/api/service-mesh/services")
async def get_service_mesh_services():
    """获取服务网格服务列表"""
    try:
        services = service_mesh.get_all_services()
        return services
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get services: {e}")

# 服务网格流量规则端点
@app.get("/api/service-mesh/traffic-rules")
async def get_service_mesh_traffic_rules():
    """获取服务网格流量规则"""
    try:
        rules = service_mesh.get_all_traffic_rules()
        return rules
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get traffic rules: {e}")

# 服务网格安全策略端点
@app.get("/api/service-mesh/security-policies")
async def get_service_mesh_security_policies():
    """获取服务网格安全策略"""
    try:
        policies = service_mesh.get_all_security_policies()
        return policies
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get security policies: {e}")

# 自动扩缩容状态端点
@app.get("/api/auto-scaling/status")
async def get_auto_scaling_status():
    """获取自动扩缩容状态"""
    try:
        status = auto_scaling_manager.get_auto_scaling_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get auto scaling status: {e}")

# 自动扩缩容配置端点
@app.get("/api/auto-scaling/config/{service_name}")
async def get_auto_scaling_config(service_name: str):
    """获取服务的自动扩缩容配置"""
    try:
        config = auto_scaling_manager.get_scaling_config(service_name)
        if not config:
            raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
        return config
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get auto scaling config: {e}")

# 自动扩缩容事件端点
@app.get("/api/auto-scaling/events")
async def get_auto_scaling_events():
    """获取自动扩缩容事件"""
    try:
        events = auto_scaling_manager.get_scaling_events()
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get auto scaling events: {e}")

# 多区域部署状态端点
@app.get("/api/multi-region/status")
async def get_multi_region_status():
    """获取多区域部署状态"""
    try:
        status = multi_region_manager.get_multi_region_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get multi-region status: {e}")

# 多区域部署区域列表端点
@app.get("/api/multi-region/regions")
async def get_multi_region_regions():
    """获取多区域部署区域列表"""
    try:
        regions = multi_region_manager.get_all_regions()
        return regions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get regions: {e}")

# 多区域部署路由规则端点
@app.get("/api/multi-region/routing-rules")
async def get_multi_region_routing_rules():
    """获取多区域部署路由规则"""
    try:
        rules = multi_region_manager.get_all_routing_rules()
        return rules
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get routing rules: {e}")

# 反馈收集端点
class FeedbackRequest(BaseModel):
    """反馈请求模型"""
    session_id: str
    input_text: str
    system_response: Dict
    feedback_type: str
    feedback_details: Optional[Dict] = None
    confidence_score: Optional[float] = None
    user_correction: Optional[str] = None

@app.post("/api/feedback/submit")
async def submit_feedback(request: FeedbackRequest):
    """提交用户反馈"""
    try:
        result = await feedback_collector.submit_feedback(
            session_id=request.session_id,
            input_text=request.input_text,
            system_response=request.system_response,
            feedback_type=request.feedback_type,
            feedback_details=request.feedback_details,
            confidence_score=request.confidence_score,
            user_correction=request.user_correction
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit feedback: {e}")

@app.get("/api/feedback/stats")
async def get_feedback_stats():
    """获取反馈统计信息"""
    try:
        stats = await feedback_collector.get_feedback_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get feedback stats: {e}")

# Prometheus指标端点
@app.get("/health/metrics")
async def metrics():
    """Prometheus指标端点"""
    try:
        content, headers = await monitoring.get_metrics()
        return content
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        return f"Error: {str(e)}"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api_gateway:app", host="0.0.0.0", port=8000, reload=True)
