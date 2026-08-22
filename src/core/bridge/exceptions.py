"""
Bridge Server 异常处理模块

提供统一的异常体系，将底层异常（网络、API、业务）转换为上层可理解的业务异常。

异常层级:
    BridgeException (基类)
    ├── NetworkException (网络错误)
    │   ├── ConnectionTimeout
    │   ├── ConnectionRefused
    │   └── DNSResolutionError
    ├── APIException (API 错误)
    │   ├── AuthenticationError (401)
    │   ├── AuthorizationError (403)
    │   ├── NotFoundError (404)
    │   ├── RateLimitError (429)
    │   └── ServerError (5xx)
    ├── BusinessException (业务错误)
    │   ├── ValidationError
    │   ├── IdempotencyError
    │   └── AgentCommunicationError
    └── UnknownException (未知错误)
"""

import logging
import traceback
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """错误码枚举"""
    # 网络错误 (1xxx)
    NETWORK_ERROR = "BRIDGE_1001"
    CONNECTION_TIMEOUT = "BRIDGE_1002"
    CONNECTION_REFUSED = "BRIDGE_1003"
    DNS_ERROR = "BRIDGE_1004"

    # API 错误 (2xxx)
    API_ERROR = "BRIDGE_2001"
    AUTH_ERROR = "BRIDGE_2002"
    FORBIDDEN = "BRIDGE_2003"
    NOT_FOUND = "BRIDGE_2004"
    RATE_LIMIT = "BRIDGE_2005"
    SERVER_ERROR = "BRIDGE_2006"

    # 业务错误 (3xxx)
    VALIDATION_ERROR = "BRIDGE_3001"
    IDEMPOTENCY_ERROR = "BRIDGE_3002"
    AGENT_ERROR = "BRIDGE_3003"
    MEMORY_ERROR = "BRIDGE_3004"

    # 未知错误 (9xxx)
    UNKNOWN_ERROR = "BRIDGE_9001"


class BridgeException(Exception):
    """Bridge 层异常基类"""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.cause = cause
        self.context = context or {}
        self.timestamp = datetime.now().isoformat()

        self._log_error()

    def _log_error(self):
        """记录错误日志"""
        log_data = {
            "code": self.code.value,
            "message": self.message,
            "details": self.details,
            "context": self.context,
            "timestamp": self.timestamp,
        }
        if self.cause:
            log_data["cause"] = str(self.cause)
            log_data["traceback"] = traceback.format_exc()

        logger.error(f"Bridge Exception: {log_data}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于 API 响应）"""
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "details": self.details,
                "timestamp": self.timestamp,
            }
        }


# ============================================================================
# 网络异常
# ============================================================================

class NetworkException(BridgeException):
    """网络错误基类"""
    pass


class ConnectionTimeout(NetworkException):
    """连接超时"""

    def __init__(
        self,
        message: str = "连接超时",
        url: Optional[str] = None,
        timeout: Optional[float] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=ErrorCode.CONNECTION_TIMEOUT,
            details={"url": url, "timeout": timeout},
            **kwargs
        )


class ConnectionRefused(NetworkException):
    """连接被拒绝"""

    def __init__(
        self,
        message: str = "连接被拒绝",
        url: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=ErrorCode.CONNECTION_REFUSED,
            details={"url": url},
            **kwargs
        )


class DNSResolutionError(NetworkException):
    """DNS 解析错误"""

    def __init__(
        self,
        message: str = "DNS 解析失败",
        hostname: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=ErrorCode.DNS_ERROR,
            details={"hostname": hostname},
            **kwargs
        )


# ============================================================================
# API 异常
# ============================================================================

class APIException(BridgeException):
    """API 错误基类"""
    pass


class AuthenticationError(APIException):
    """认证失败 (401)"""

    def __init__(
        self,
        message: str = "认证失败，请检查 API Key",
        status_code: int = 401,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=ErrorCode.AUTH_ERROR,
            details={"status_code": status_code},
            **kwargs
        )


class AuthorizationError(APIException):
    """权限不足 (403)"""

    def __init__(
        self,
        message: str = "权限不足",
        status_code: int = 403,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=ErrorCode.FORBIDDEN,
            details={"status_code": status_code},
            **kwargs
        )


class NotFoundError(APIException):
    """资源不存在 (404)"""

    def __init__(
        self,
        message: str = "资源不存在",
        resource: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=ErrorCode.NOT_FOUND,
            details={"resource": resource},
            **kwargs
        )


class RateLimitError(APIException):
    """请求频率超限 (429)"""

    def __init__(
        self,
        message: str = "请求频率超限，请稍后重试",
        retry_after: Optional[int] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=ErrorCode.RATE_LIMIT,
            details={"retry_after": retry_after},
            **kwargs
        )


class ServerError(APIException):
    """服务器错误 (5xx)"""

    def __init__(
        self,
        message: str = "服务器内部错误",
        status_code: int = 500,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=ErrorCode.SERVER_ERROR,
            details={"status_code": status_code},
            **kwargs
        )


# ============================================================================
# 业务异常
# ============================================================================

class BusinessException(BridgeException):
    """业务错误基类"""
    pass


class ValidationError(BusinessException):
    """参数验证错误"""

    def __init__(
        self,
        message: str = "参数验证失败",
        field: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=ErrorCode.VALIDATION_ERROR,
            details={"field": field},
            **kwargs
        )


class IdempotencyError(BusinessException):
    """幂等性冲突"""

    def __init__(
        self,
        message: str = "检测到重复请求",
        idempotency_key: Optional[str] = None,
        original_request_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=ErrorCode.IDEMPOTENCY_ERROR,
            details={
                "idempotency_key": idempotency_key,
                "original_request_id": original_request_id
            },
            **kwargs
        )


class AgentCommunicationError(BusinessException):
    """Agent 通信错误"""

    def __init__(
        self,
        message: str = "Agent 通信失败",
        agent_name: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=ErrorCode.AGENT_ERROR,
            details={"agent_name": agent_name},
            **kwargs
        )


class MemoryError(BusinessException):
    """记忆系统错误"""

    def __init__(
        self,
        message: str = "记忆操作失败",
        operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            code=ErrorCode.MEMORY_ERROR,
            details={"operation": operation},
            **kwargs
        )


# ============================================================================
# 未知异常
# ============================================================================

class UnknownException(BridgeException):
    """未知错误"""

    def __init__(
        self,
        message: str = "发生未知错误",
        **kwargs
    ):
        super().__init__(
            message=message,
            code=ErrorCode.UNKNOWN_ERROR,
            **kwargs
        )


# ============================================================================
# 异常映射表
# ============================================================================

# HTTP 状态码到异常的映射
HTTP_STATUS_TO_EXCEPTION = {
    401: AuthenticationError,
    403: AuthorizationError,
    404: NotFoundError,
    429: RateLimitError,
    500: ServerError,
    502: ServerError,
    503: ServerError,
    504: ServerError,
}

# httpx 异常到 Bridge 异常的映射
HTTPX_EXCEPTION_MAP = {
    "ConnectTimeout": ConnectionTimeout,
    "ReadTimeout": ConnectionTimeout,
    "WriteTimeout": ConnectionTimeout,
    "ConnectError": ConnectionRefused,
    "PoolTimeout": ConnectionTimeout,
}


def map_http_exception(status_code: int, message: str = None) -> APIException:
    """将 HTTP 状态码映射为对应的异常"""
    exception_class = HTTP_STATUS_TO_EXCEPTION.get(
        status_code,
        APIException
    )
    return exception_class(message=message or f"HTTP {status_code} 错误")


def map_httpx_exception(exc: Exception) -> NetworkException:
    """将 httpx 异常映射为 Bridge 异常"""
    exc_name = type(exc).__name__
    exception_class = HTTPX_EXCEPTION_MAP.get(
        exc_name,
        NetworkException
    )
    return exception_class(
        message=str(exc),
        cause=exc
    )
