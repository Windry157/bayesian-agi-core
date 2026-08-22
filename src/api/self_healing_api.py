#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bayesian-AGI-Core API Gateway - 自愈服务模块
提供标准化的故障修复和自动化运维接口
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import logging

from src.core.observability.self_healing import (
    self_healing_engine,
    RemediationPlaybooks,
    RemediationStatus
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/self-healing", tags=["self-healing"])


# 请求模型
class ExecuteActionRequest(BaseModel):
    """执行修复动作请求"""
    action_id: str = Field(..., description="修复动作ID")
    parameters: Optional[Dict[str, Any]] = Field({}, description="动作参数")


class ExecutePlaybookRequest(BaseModel):
    """执行修复剧本请求"""
    playbook_name: str = Field(..., description="剧本名称")


# 响应模型
class ActionInfo(BaseModel):
    """动作信息"""
    id: str = Field(..., description="动作ID")
    name: str = Field(..., description="动作名称")
    description: str = Field(..., description="动作描述")
    priority: str = Field(..., description="优先级")
    timeout: int = Field(..., description="超时时间(秒)")
    retries: int = Field(..., description="重试次数")


class ExecutionResult(BaseModel):
    """执行结果"""
    execution_id: str = Field(..., description="执行ID")
    action_id: str = Field(..., description="动作ID")
    status: str = Field(..., description="状态: pending/running/success/failed/timeout")
    started_at: float = Field(..., description="开始时间戳")
    completed_at: Optional[float] = Field(None, description="完成时间戳")
    error_message: Optional[str] = Field(None, description="错误信息")


class PlaybookInfo(BaseModel):
    """剧本信息"""
    name: str = Field(..., description="剧本名称")
    description: str = Field(..., description="剧本描述")
    actions: List[str] = Field([], description="包含的动作列表")


# API 端点
@router.get("/actions", response_model=List[ActionInfo])
async def list_actions():
    """获取所有可用的修复动作"""
    try:
        actions = self_healing_engine.actions
        return [
            ActionInfo(
                id=action.id,
                name=action.name,
                description=action.description,
                priority=action.priority.value,
                timeout=action.timeout,
                retries=action.retries
            )
            for action in actions.values()
        ]
    except Exception as e:
        logger.error(f"获取动作列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/actions/{action_id}", response_model=ActionInfo)
async def get_action(action_id: str):
    """获取单个动作详情"""
    try:
        action = self_healing_engine.actions.get(action_id)
        if not action:
            raise HTTPException(status_code=404, detail=f"动作 {action_id} 不存在")
        
        return ActionInfo(
            id=action.id,
            name=action.name,
            description=action.description,
            priority=action.priority.value,
            timeout=action.timeout,
            retries=action.retries
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取动作详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/actions/{action_id}/execute", response_model=ExecutionResult)
async def execute_action(action_id: str, request: Optional[ExecuteActionRequest] = None):
    """执行单个修复动作"""
    try:
        params = request.parameters if request else {}
        execution = self_healing_engine.execute_action(action_id, **params)
        
        return ExecutionResult(
            execution_id=execution.id,
            action_id=execution.action_id,
            status=execution.status.value,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            error_message=execution.error_message
        )
    except Exception as e:
        logger.error(f"执行动作失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/playbooks", response_model=List[PlaybookInfo])
async def list_playbooks():
    """获取所有可用的修复剧本"""
    try:
        playbooks = [
            {"name": "high_error_rate", "description": "高错误率修复剧本", "actions": RemediationPlaybooks.high_error_rate()},
            {"name": "high_latency", "description": "高延迟修复剧本", "actions": RemediationPlaybooks.high_latency()},
            {"name": "db_connection_issue", "description": "数据库连接问题修复剧本", "actions": RemediationPlaybooks.db_connection_issue()},
            {"name": "memory_exhaustion", "description": "内存耗尽修复剧本", "actions": RemediationPlaybooks.memory_exhaustion()},
        ]
        
        return [
            PlaybookInfo(
                name=pb["name"],
                description=pb["description"],
                actions=pb["actions"]
            )
            for pb in playbooks
        ]
    except Exception as e:
        logger.error(f"获取剧本列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/playbooks/{playbook_name}", response_model=PlaybookInfo)
async def get_playbook(playbook_name: str):
    """获取单个剧本详情"""
    try:
        playbook_map = {
            "high_error_rate": {"description": "高错误率修复剧本", "actions": RemediationPlaybooks.high_error_rate()},
            "high_latency": {"description": "高延迟修复剧本", "actions": RemediationPlaybooks.high_latency()},
            "db_connection_issue": {"description": "数据库连接问题修复剧本", "actions": RemediationPlaybooks.db_connection_issue()},
            "memory_exhaustion": {"description": "内存耗尽修复剧本", "actions": RemediationPlaybooks.memory_exhaustion()},
        }
        
        pb = playbook_map.get(playbook_name)
        if not pb:
            raise HTTPException(status_code=404, detail=f"剧本 {playbook_name} 不存在")
        
        return PlaybookInfo(
            name=playbook_name,
            description=pb["description"],
            actions=pb["actions"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取剧本详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/playbooks/{playbook_name}/execute")
async def execute_playbook(playbook_name: str):
    """执行修复剧本"""
    try:
        playbook_map = {
            "high_error_rate": RemediationPlaybooks.high_error_rate,
            "high_latency": RemediationPlaybooks.high_latency,
            "db_connection_issue": RemediationPlaybooks.db_connection_issue,
            "memory_exhaustion": RemediationPlaybooks.memory_exhaustion,
        }
        
        playbook_func = playbook_map.get(playbook_name)
        if not playbook_func:
            raise HTTPException(status_code=404, detail=f"剧本 {playbook_name} 不存在")
        
        results = self_healing_engine.execute_playbook(playbook_func())
        
        return {
            "status": "success",
            "playbook": playbook_name,
            "executions": [
                {
                    "execution_id": r.id,
                    "action_id": r.action_id,
                    "status": r.status.value,
                    "error_message": r.error_message
                }
                for r in results
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"执行剧本失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/execution-history")
async def get_execution_history(limit: int = 50):
    """获取执行历史"""
    try:
        history = self_healing_engine.get_execution_history(limit=limit)
        return [
            {
                "execution_id": exec.id,
                "action_id": exec.action_id,
                "status": exec.status.value,
                "started_at": exec.started_at,
                "completed_at": exec.completed_at,
                "error_message": exec.error_message,
                "retry_count": exec.retry_count
            }
            for exec in history
        ]
    except Exception as e:
        logger.error(f"获取执行历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/running-actions")
async def get_running_actions():
    """获取正在执行的动作"""
    try:
        running = self_healing_engine.get_running_actions()
        return {"running_actions": running}
    except Exception as e:
        logger.error(f"获取运行中动作失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_self_healing_status():
    """获取自愈服务状态"""
    return {
        "status": "healthy",
        "component": "self-healing-service",
        "features": [
            "remediation-actions",
            "remediation-playbooks",
            "execution-tracking"
        ],
        "registered_actions": len(self_healing_engine.actions),
        "running_actions": len(self_healing_engine.get_running_actions())
    }