"""
Bridge 模块 - OpenClaw 生态对接

提供与 OpenCode CLI Agent 的通信能力，支持标准 OpenClaw 协议。

主要组件:
    - BridgeServer: REST API 服务
    - exceptions: 统一异常处理
    - idempotency: 幂等性检查
    - parallel_executor: 异步并行执行器
"""

from .bridge_server import BridgeConfig, BridgeServer, create_bridge_server, get_bridge_server
from .exceptions import (
    BridgeException,
    ErrorCode,
    NetworkException,
    APIException,
    BusinessException,
    AuthenticationError,
    ConnectionTimeout,
    ValidationError,
    IdempotencyError,
)
from .idempotency import IdempotencyChecker, get_idempotency_checker
from .parallel_executor import (
    AsyncParallelExecutor,
    ParallelResult,
    TaskResult,
    TaskStatus,
)

__all__ = [
    # Bridge Server
    "BridgeServer",
    "BridgeConfig",
    "get_bridge_server",
    "create_bridge_server",
    # Exceptions
    "BridgeException",
    "ErrorCode",
    "NetworkException",
    "APIException",
    "BusinessException",
    "AuthenticationError",
    "ConnectionTimeout",
    "ValidationError",
    "IdempotencyError",
    # Idempotency
    "IdempotencyChecker",
    "get_idempotency_checker",
    # Parallel Executor
    "AsyncParallelExecutor",
    "ParallelResult",
    "TaskResult",
    "TaskStatus",
]
