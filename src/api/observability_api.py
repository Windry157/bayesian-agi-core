#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bayesian-AGI-Core API Gateway - 可观测性服务模块
提供标准化的监控、指标和告警接口
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import logging

from src.core.observability.observability_center import ObservabilityCenter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/observability", tags=["observability"])

# 初始化可观测性中心
observability_center = ObservabilityCenter()


# 请求模型
class CostRecordRequest(BaseModel):
    """成本记录请求"""
    input_tokens: int = Field(0, description="输入Token数")
    output_tokens: int = Field(0, description="输出Token数")
    duration_ms: int = Field(0, description="计算时长(毫秒)")
    model_name: str = Field("unknown", description="模型名称")


class AlertTriggerRequest(BaseModel):
    """告警触发请求"""
    alert_id: str = Field(..., description="告警ID")
    message: str = Field(..., description="告警消息")
    level: str = Field("WARNING", description="告警级别: INFO/WARNING/CRITICAL")
    metadata: Optional[Dict[str, Any]] = Field(None, description="附加元数据")


# 响应模型
class CostSummary(BaseModel):
    """成本摘要"""
    total_input_tokens: int = Field(0, description="总输入Token")
    total_output_tokens: int = Field(0, description="总输出Token")
    token_cost_usd: float = Field(0.0, description="Token成本(USD)")
    compute_cost_usd: float = Field(0.0, description="计算成本(USD)")
    total_cost_usd: float = Field(0.0, description="总成本(USD)")
    period_hours: int = Field(0, description="统计周期(小时)")


class AlertInfo(BaseModel):
    """告警信息"""
    alert_id: str = Field(..., description="告警ID")
    message: str = Field(..., description="告警消息")
    level: str = Field(..., description="告警级别")
    timestamp: datetime = Field(..., description="触发时间")
    resolved: bool = Field(False, description="是否已解决")
    metadata: Optional[Dict[str, Any]] = Field(None, description="附加元数据")


class MetricsData(BaseModel):
    """指标数据"""
    name: str = Field(..., description="指标名称")
    value: Union[int, float] = Field(..., description="指标值")
    timestamp: datetime = Field(..., description="时间戳")
    labels: Optional[Dict[str, str]] = Field(None, description="标签")


class DashboardData(BaseModel):
    """仪表盘数据"""
    cost: CostSummary = Field(..., description="成本摘要")
    active_alerts: List[AlertInfo] = Field([], description="活动告警列表")
    recent_errors: List[Dict[str, Any]] = Field([], description="最近错误")
    performance: Dict[str, Any] = Field({}, description="性能指标")


# API 端点
@router.post("/cost/record")
async def record_cost(request: CostRecordRequest):
    """记录成本消耗"""
    try:
        observability_center.record_token_usage(
            input_tokens=request.input_tokens,
            output_tokens=request.output_tokens
        )
        observability_center.record_compute_time(duration_ms=request.duration_ms)
        return {"status": "success", "message": "成本记录成功"}
    except Exception as e:
        logger.error(f"成本记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cost/summary", response_model=CostSummary)
async def get_cost_summary(hours: int = 24):
    """获取成本摘要"""
    try:
        summary = observability_center.cost_tracker.get_cost_summary(hours=hours)
        return CostSummary(
            total_input_tokens=summary.get("total_input_tokens", 0),
            total_output_tokens=summary.get("total_output_tokens", 0),
            token_cost_usd=summary.get("token_cost_usd", 0.0),
            compute_cost_usd=summary.get("compute_cost_usd", 0.0),
            total_cost_usd=summary.get("total_cost_usd", 0.0),
            period_hours=hours
        )
    except Exception as e:
        logger.error(f"获取成本摘要失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/trigger")
async def trigger_alert(request: AlertTriggerRequest):
    """触发告警"""
    try:
        observability_center.alert_manager.trigger_alert(
            alert_id=request.alert_id,
            message=request.message,
            level=request.level,
            **(request.metadata or {})
        )
        return {"status": "success", "message": "告警已触发"}
    except Exception as e:
        logger.error(f"触发告警失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts", response_model=List[AlertInfo])
async def get_active_alerts():
    """获取活动告警列表"""
    try:
        alerts = observability_center.alert_manager.get_active_alerts()
        return [
            AlertInfo(
                alert_id=alert["alert_id"],
                message=alert["message"],
                level=alert["level"],
                timestamp=alert["timestamp"],
                resolved=alert.get("resolved", False),
                metadata=alert.get("metadata")
            )
            for alert in alerts
        ]
    except Exception as e:
        logger.error(f"获取告警列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    """解决告警"""
    try:
        observability_center.alert_manager.resolve_alert(alert_id)
        return {"status": "success", "message": f"告警 {alert_id} 已解决"}
    except Exception as e:
        logger.error(f"解决告警失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics", response_model=List[MetricsData])
async def get_metrics():
    """获取指标数据"""
    try:
        metrics = observability_center.get_all_metrics()
        return [
            MetricsData(
                name=metric["name"],
                value=metric["value"],
                timestamp=metric["timestamp"],
                labels=metric.get("labels")
            )
            for metric in metrics
        ]
    except Exception as e:
        logger.error(f"获取指标失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard", response_model=DashboardData)
async def get_dashboard():
    """获取仪表盘数据"""
    try:
        dashboard = observability_center.get_dashboard_data()
        return DashboardData(
            cost=CostSummary(
                total_input_tokens=dashboard["cost"].get("total_input_tokens", 0),
                total_output_tokens=dashboard["cost"].get("total_output_tokens", 0),
                token_cost_usd=dashboard["cost"].get("token_cost_usd", 0.0),
                compute_cost_usd=dashboard["cost"].get("compute_cost_usd", 0.0),
                total_cost_usd=dashboard["cost"].get("total_cost_usd", 0.0),
                period_hours=24
            ),
            active_alerts=[
                AlertInfo(
                    alert_id=alert["alert_id"],
                    message=alert["message"],
                    level=alert["level"],
                    timestamp=alert["timestamp"],
                    resolved=alert.get("resolved", False),
                    metadata=alert.get("metadata")
                )
                for alert in dashboard.get("active_alerts", [])
            ],
            recent_errors=dashboard.get("recent_errors", []),
            performance=dashboard.get("performance", {})
        )
    except Exception as e:
        logger.error(f"获取仪表盘数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_observability_status():
    """获取可观测性服务状态"""
    return {
        "status": "healthy",
        "component": "observability-service",
        "features": [
            "cost-tracking",
            "alert-management",
            "metrics-collection",
            "dashboard"
        ]
    }