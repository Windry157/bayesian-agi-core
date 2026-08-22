#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bayesian-AGI-Core API Gateway - 安全服务模块
提供标准化的安全验证和沙箱执行接口
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import logging

from src.core.safety.security_framework import SecurityFramework

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/security", tags=["security"])

# 初始化安全框架
security_framework = SecurityFramework()


# 请求模型
class ValidateInputRequest(BaseModel):
    """输入验证请求"""
    input_data: str = Field(..., description="待验证的输入数据")
    validation_type: str = Field("full", description="验证类型: full/syntax/semantic")


class CodeExecutionRequest(BaseModel):
    """代码执行请求"""
    code: str = Field(..., description="待执行的代码")
    timeout: int = Field(30, description="超时时间(秒)")
    max_memory_mb: int = Field(512, description="最大内存(MB)")


class SQLValidationRequest(BaseModel):
    """SQL验证请求"""
    query: str = Field(..., description="待验证的SQL查询")
    allowed_tables: Optional[List[str]] = Field(None, description="允许访问的表名列表")


class ShellCommandRequest(BaseModel):
    """Shell命令请求"""
    command: str = Field(..., description="命令")
    args: Optional[List[str]] = Field(None, description="参数列表")


# 响应模型
class ValidationResult(BaseModel):
    """验证结果"""
    valid: bool = Field(..., description="是否通过验证")
    errors: List[str] = Field([], description="错误列表")
    warnings: List[str] = Field([], description="警告列表")
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息")


class ExecutionResult(BaseModel):
    """执行结果"""
    success: bool = Field(..., description="是否成功")
    output: Optional[str] = Field(None, description="输出结果")
    error: Optional[str] = Field(None, description="错误信息")
    duration_ms: int = Field(..., description="执行时长(毫秒)")


# API 端点
@router.post("/validate", response_model=ValidationResult)
async def validate_input(request: ValidateInputRequest):
    """验证输入安全性"""
    try:
        result = security_framework.validate_input(
            request.input_data,
            validation_type=request.validation_type
        )
        return ValidationResult(
            valid=result["valid"],
            errors=result.get("errors", []),
            warnings=result.get("warnings", []),
            details=result.get("details")
        )
    except Exception as e:
        logger.error(f"输入验证失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute", response_model=ExecutionResult)
async def execute_in_sandbox(request: CodeExecutionRequest):
    """在沙箱中执行代码"""
    try:
        result = security_framework.execute_safely(
            request.code,
            timeout=request.timeout,
            max_memory_mb=request.max_memory_mb
        )
        return ExecutionResult(
            success=result["success"],
            output=result.get("output"),
            error=result.get("error"),
            duration_ms=result.get("duration_ms", 0)
        )
    except Exception as e:
        logger.error(f"沙箱执行失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate/sql", response_model=ValidationResult)
async def validate_sql(request: SQLValidationRequest):
    """验证SQL查询安全性"""
    try:
        result = security_framework.validate_sql(
            request.query,
            allowed_tables=request.allowed_tables
        )
        return ValidationResult(
            valid=result["valid"],
            errors=result.get("errors", []),
            warnings=result.get("warnings", []),
            details=result.get("details")
        )
    except Exception as e:
        logger.error(f"SQL验证失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate/shell", response_model=ValidationResult)
async def validate_shell(request: ShellCommandRequest):
    """验证Shell命令安全性"""
    try:
        result = security_framework.validate_shell(
            request.command,
            args=request.args
        )
        return ValidationResult(
            valid=result["valid"],
            errors=result.get("errors", []),
            warnings=result.get("warnings", []),
            details=result.get("details")
        )
    except Exception as e:
        logger.error(f"Shell验证失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_security_status():
    """获取安全服务状态"""
    return {
        "status": "healthy",
        "component": "security-service",
        "features": [
            "input-validation",
            "code-execution",
            "sql-validation",
            "shell-validation"
        ]
    }