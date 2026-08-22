"""
错误处理装饰器 - 统一处理异步函数的异常情况
"""
import functools
import logging
from typing import Any, Callable, Optional, TypeVar

T = TypeVar('T')
logger = logging.getLogger("gateway.error_handler")


def handle_api_errors(
    default_value: Any = None,
    error_message: Optional[str] = None,
    log_level: int = logging.ERROR
):
    """
    API 错误处理装饰器

    Args:
        default_value: 发生异常时返回的默认值，如果是可调用对象则传入异常并调用
        error_message: 自定义错误消息前缀，如果为 None 则使用函数名
        log_level: 日志级别，默认为 ERROR

    Returns:
        装饰器函数
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                message_prefix = error_message or f"{func.__name__}"
                logger.log(log_level, f"{message_prefix} failed: {e}")

                if callable(default_value):
                    return default_value(e)
                return default_value

        return async_wrapper
    return decorator
