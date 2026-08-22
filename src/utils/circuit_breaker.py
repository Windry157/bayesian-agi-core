#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
熔断器模式实现
- 熔断器状态管理
- 错误计数和恢复机制
- 自动降级策略
"""

import time
import enum
import threading
import functools
from typing import Callable, Any, Optional, Dict, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from src.utils.structured_logging import get_logger

logger = get_logger("circuit_breaker")


class CircuitState(enum.Enum):
    """熔断器状态"""
    CLOSED = "closed"  # 正常状态
    OPEN = "open"  # 熔断状态，拒绝请求
    HALF_OPEN = "half_open"  # 半开状态，尝试恢复


@dataclass
class CircuitMetrics:
    """熔断器指标"""
    success_count: int = 0
    failure_count: int = 0
    timeout_count: int = 0
    total_requests: int = 0
    last_failure_time: Optional[datetime] = None
    failure_rate: float = 0.0


class CircuitBreaker:
    """熔断器实现"""
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Tuple[Exception, ...] = (Exception,),
        fallback_function: Optional[Callable] = None,
    ):
        """
        初始化熔断器
        
        Args:
            name: 熔断器名称
            failure_threshold: 失败阈值，超过后打开熔断器
            recovery_timeout: 恢复超时时间（秒）
            expected_exception: 预期的异常类型
            fallback_function: 降级函数
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.fallback_function = fallback_function
        
        self._state = CircuitState.CLOSED
        self._metrics = CircuitMetrics()
        self._last_open_time: Optional[datetime] = None
        self._lock = threading.Lock()
    
    def _reset(self):
        """重置熔断器状态"""
        with self._lock:
            self._reset_unlocked()

    def _trip(self):
        """熔断"""
        with self._lock:
            self._trip_unlocked()
    
    def _should_attempt_reset(self) -> bool:
        """检查是否应该尝试重置"""
        if self._state != CircuitState.OPEN:
            return False
        
        if self._last_open_time is None:
            return False
        
        elapsed = (datetime.now() - self._last_open_time).total_seconds()
        return elapsed >= self.recovery_timeout
    
    def _record_success(self):
        """记录成功请求"""
        with self._lock:
            self._metrics.success_count += 1
            self._metrics.total_requests += 1
            self._update_failure_rate_unlocked()

            if self._state == CircuitState.HALF_OPEN:
                self._reset_unlocked()
    
    def _record_failure(self):
        """记录失败请求"""
        with self._lock:
            self._metrics.failure_count += 1
            self._metrics.total_requests += 1
            self._metrics.last_failure_time = datetime.now()
            self._update_failure_rate_unlocked()

            if self._state == CircuitState.CLOSED:
                if self._metrics.failure_count >= self.failure_threshold:
                    self._trip_unlocked()
            elif self._state == CircuitState.HALF_OPEN:
                self._trip_unlocked()

    def _update_failure_rate_unlocked(self):
        """更新失败率（无锁版本，调用前必须持有锁）"""
        if self._metrics.total_requests > 0:
            self._metrics.failure_rate = (
                self._metrics.failure_count / self._metrics.total_requests
            )

    def _trip_unlocked(self):
        """熔断（无锁版本，调用前必须持有锁）"""
        self._state = CircuitState.OPEN
        self._last_open_time = datetime.now()
        logger.warning(
            f"Circuit '{self.name}' tripped to OPEN state (failures: {self._metrics.failure_count}, rate: {self._metrics.failure_rate:.2f})"
        )

    def _reset_unlocked(self):
        """重置熔断器状态（无锁版本，调用前必须持有锁）"""
        self._state = CircuitState.CLOSED
        self._metrics = CircuitMetrics()
        self._last_open_time = None
        logger.info(f"Circuit '{self.name}' reset to CLOSED state")
    
    def _check_state(self):
        """检查状态"""
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                    logger.info(f"Circuit '{self.name}' transitioning to HALF_OPEN state")
                    return

                raise CircuitOpenError(
                    f"Circuit '{self.name}' is OPEN",
                    circuit_name=self.name,
                    last_failure_time=self._metrics.last_failure_time,
                    failure_count=self._metrics.failure_count
                )

    def get_state(self) -> CircuitState:
        """获取当前状态"""
        with self._lock:
            return self._state

    def get_metrics(self) -> CircuitMetrics:
        """获取指标（返回副本保证线程安全）"""
        with self._lock:
            return CircuitMetrics(
                success_count=self._metrics.success_count,
                failure_count=self._metrics.failure_count,
                timeout_count=self._metrics.timeout_count,
                total_requests=self._metrics.total_requests,
                last_failure_time=self._metrics.last_failure_time,
                failure_rate=self._metrics.failure_rate
            )
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        执行函数，应用熔断保护
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
        
        Returns:
            函数执行结果或降级结果
        
        Raises:
            CircuitOpenError: 当熔断器打开时
        """
        self._check_state()
        
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except self.expected_exception as e:
            self._record_failure()
            
            if self.fallback_function is not None:
                logger.warning(
                    f"Executing fallback for circuit '{self.name}'",
                    error=str(e)
                )
                return self.fallback_function(*args, **kwargs)
            
            raise
        except Exception as e:
            logger.error(f"Unexpected error in circuit '{self.name}': {e}")
            self._record_failure()
            raise


class CircuitOpenError(Exception):
    """熔断器打开错误"""
    
    def __init__(
        self,
        message: str,
        circuit_name: str,
        last_failure_time: Optional[datetime],
        failure_count: int
    ):
        super().__init__(message)
        self.circuit_name = circuit_name
        self.last_failure_time = last_failure_time
        self.failure_count = failure_count


# 全局熔断器管理
_circuit_breakers: Dict[str, CircuitBreaker] = {}
_circuit_breakers_lock = threading.Lock()


def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    """获取或创建熔断器"""
    with _circuit_breakers_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = CircuitBreaker(name, **kwargs)
        return _circuit_breakers[name]


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    fallback_function: Optional[Callable] = None,
):
    """
    熔断器装饰器
    
    Args:
        name: 熔断器名称
        failure_threshold: 失败阈值
        recovery_timeout: 恢复超时
        fallback_function: 降级函数
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            breaker = get_circuit_breaker(
                name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                fallback_function=fallback_function
            )
            return breaker.execute(func, *args, **kwargs)
        
        return wrapper
    
    return decorator


class CircuitBreakerManager:
    """熔断器管理器"""

    @staticmethod
    def list_circuits() -> Dict[str, Dict]:
        """列出所有熔断器状态"""
        with _circuit_breakers_lock:
            result = {}
            for name, breaker in _circuit_breakers.items():
                metrics = breaker.get_metrics()
                result[name] = {
                    'state': breaker.get_state().value,
                    'success_count': metrics.success_count,
                    'failure_count': metrics.failure_count,
                    'total_requests': metrics.total_requests,
                    'failure_rate': metrics.failure_rate,
                    'last_failure_time': metrics.last_failure_time.isoformat() if metrics.last_failure_time else None
                }
            return result

    @staticmethod
    def reset_circuit(name: str):
        """重置指定熔断器"""
        with _circuit_breakers_lock:
            if name in _circuit_breakers:
                _circuit_breakers[name]._reset()
                logger.info(f"Circuit '{name}' manually reset")

    @staticmethod
    def reset_all():
        """重置所有熔断器"""
        with _circuit_breakers_lock:
            for name in _circuit_breakers:
                _circuit_breakers[name]._reset()
            logger.info("All circuits manually reset")
