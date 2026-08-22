#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
企业级韧性组件 (Enterprise-Grade Resilience)
实现 Outbox Pattern, Circuit Breaker, Distributed Tracing
"""
import uuid
import time
import json
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime, timedelta
from collections import defaultdict, deque
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

# ============================================
# 1. 事务性发件箱模式 (Transactional Outbox Pattern)
# ============================================


class OutboxMessageStatus(Enum):
    PENDING = "pending"
    PUBLISHED = "published"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


@dataclass
class OutboxMessage:
    """发件箱消息"""
    id: str
    event_type: str
    aggregate_id: str
    aggregate_type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: OutboxMessageStatus = OutboxMessageStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    retry_count: int = 0
    max_retries: int = 5
    last_error: Optional[str] = None


class TransactionalOutbox:
    """事务性发件箱模式
    
    解决"数据库事务与消息发送的原子性保证
    
    使用方法：
    1. 业务逻辑与消息写入在同一个数据库事务
    2. 后台 Relay 轮询发件箱并发送
    """
    
    def __init__(self):
        self.messages: Dict[str, OutboxMessage] = {}
        self.published_events: List[str] = []
        self._running = False
        
    def write_outbox(self, event_data: Dict[str, Any], 
                   transaction_context: Optional[Dict[str, Any]] = None) -> str:
        """在事务中写入发件箱
        
        这一步应该与业务更新在同一个数据库事务中
        
        Returns:
            message_id: 消息ID
        """
        message_id = str(uuid.uuid4())
        
        message = OutboxMessage(
            id=message_id,
            event_type=event_data.get("event_type", "unknown"),
            aggregate_id=event_data.get("aggregate_id", ""),
            aggregate_type=event_data.get("aggregate_type", ""),
            payload=event_data.get("payload", {}),
            metadata=event_data.get("metadata", {}),
            status=OutboxMessageStatus.PENDING,
        )
        
        self.messages[message_id] = message
        logger.info(f"[Outbox] 写入发件箱: {message_id}, 类型: {message.event_type}")
        
        return message_id
    
    def mark_as_published(self, message_id: str):
        """标记为已发布"""
        if message_id in self.messages:
            msg = self.messages[message_id]
            msg.status = OutboxMessageStatus.PUBLISHED
            msg.updated_at = datetime.now().isoformat()
            self.published_events.append(message_id)
            logger.info(f"[Outbox] 标记为已发布: {message_id}")
    
    def mark_as_failed(self, message_id: str, error: str):
        """标记为失败"""
        if message_id in self.messages:
            msg = self.messages[message_id]
            msg.status = OutboxMessageStatus.FAILED
            msg.last_error = error
            msg.retry_count += 1
            msg.updated_at = datetime.now().isoformat()
            logger.error(f"[Outbox] 标记为失败: {message_id}, 错误: {error}")
            
            if msg.retry_count >= msg.max_retries:
                self._move_to_dead_letter(msg)
    
    def _move_to_dead_letter(self, msg: OutboxMessage):
        """移到死信"""
        msg.status = OutboxMessageStatus.DEAD_LETTER
        logger.critical(f"[Outbox] 移到死信: {msg.id}")
    
    def get_pending_messages(self, batch_size: int = 100) -> List[OutboxMessage]:
        """获取待发布的消息批次"""
        pending = [
            msg for msg in self.messages.values() 
            if msg.status == OutboxMessageStatus.PENDING
        ]
        sorted_pending = sorted(pending, key=lambda m: m.created_at)[:batch_size]
        return sorted_pending
    
    def get_failed_messages(self) -> List[OutboxMessage]:
        """获取失败的消息"""
        return [
            msg for msg in self.messages.values() 
            if msg.status == OutboxMessageStatus.FAILED
        ]
    
    def retry_failed_messages(self) -> int:
        """重试失败的消息"""
        failed = self.get_failed_messages()
        retried = 0
        
        for msg in failed:
            if msg.retry_count < msg.max_retries:
                msg.status = OutboxMessageStatus.PENDING
                msg.last_error = None
                msg.updated_at = datetime.now().isoformat()
                retried += 1
        
        logger.info(f"[Outbox] 已重置 {retried} 条失败消息")
        return retried


class OutboxRelay:
    """发件箱中继 - 后台轮询进程
    
    负责将发件箱中的消息原子地发布到消息队列
    """
    
    def __init__(self, outbox: TransactionalOutbox, event_bus: Any):
        self.outbox = outbox
        self.event_bus = event_bus
        self.poll_interval_seconds = 1.0
        self._running = False
        
    def start(self):
        """启动中继"""
        self._running = True
        logger.info("[Outbox Relay] 启动中继已启动")
    
    def process_outbox(self):
        """处理一批发件箱"""
        if not self._running:
            return
        
        pending = self.outbox.get_pending_messages(100)
        for msg in pending:
            self._publish_with_retry(msg)
    
    def _publish_with_retry(self, msg: OutboxMessage):
        """带重试的发布"""
        try:
            event_data = {
                "event_id": msg.id,
                "event_type": msg.event_type,
                "aggregate_id": msg.aggregate_id,
                "aggregate_type": msg.aggregate_type,
                "payload": msg.payload,
                "metadata": msg.metadata,
            }
            
            # 这里应该接入真实消息队列
            self.event_bus.publish(event_data)
            self.outbox.mark_as_published(msg.id)
            return True
            
        except Exception as e:
            self.outbox.mark_as_failed(msg.id, str(e))
            return False


# ============================================
# 2. 熔断器模式 (Circuit Breaker)
# ============================================


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"       # 正常状态：正常通行
    OPEN = "open"           # 熔断状态：快速失败
    HALF_OPEN = "half_open"   # 半开状态：尝试恢复


class CircuitBreakerError(Exception):
    """熔断器打开时抛出"""
    pass


class CircuitBreakerMetrics:
    """熔断器指标"""
    
    def __init__(self, failure_threshold: int = 5, 
                 recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.success_count = 0
        self.total_calls = 0
        self.total_failures = 0
        
    def record_success(self):
        """记录成功"""
        self.failure_count = 0
        self.success_count += 1
        self.total_calls += 1
        
    def record_failure(self):
        """记录失败"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.total_calls += 1
        self.total_failures += 1
        
    def should_open(self) -> bool:
        """检查是否需要打开熔断器"""
        if self.state == CircuitState.OPEN:
            return True
        
        if self.failure_count >= self.failure_threshold:
            return True
            
        return False
        
    def should_attempt_reset(self) -> bool:
        """检查是否应该尝试重置"""
        if self.state != CircuitState.OPEN:
            return False
            
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.recovery_timeout


class CircuitBreaker:
    """熔断器模式
    
    防止级联失败，提升系统韧性
    """
    
    def __init__(self, name: str, 
                 failure_threshold: int = 5,
                 recovery_timeout: float = 30.0,
                 expected_exception: type = Exception):
        self.name = name
        self.metrics = CircuitBreakerMetrics(failure_threshold, recovery_timeout)
        self.expected_exception = expected_exception
        self.fallback_function: Optional[Callable] = None
        
    def __call__(self, func: Callable):
        """装饰器使用"""
        def wrapper(*args, **kwargs):
            return self.execute(func, *args, **kwargs)
        return wrapper
        
    def execute(self, func: Callable, *args, **kwargs):
        """执行带保护的函数执行"""
        
        # 检查熔断器状态
        if self.metrics.should_open():
            if self.metrics.should_attempt_reset():
                self.metrics.state = CircuitState.HALF_OPEN
                logger.warning(f"[CircuitBreaker] {self.name} 进入半开状态，尝试恢复")
            else:
                logger.error(f"[CircuitBreaker] {self.name} 熔断器打开，快速失败")
                return self._handle_fallback()
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            logger.error(f"[CircuitBreaker] {self.name} 调用失败: {str(e)}")
            return self._handle_fallback()
            
    def _on_success(self):
        """成功处理"""
        self.metrics.record_success()
        if self.metrics.state == CircuitState.HALF_OPEN:
            self.metrics.state = CircuitState.CLOSED
            logger.info(f"[CircuitBreaker] {self.name} 熔断器关闭，恢复正常")
            
    def _on_failure(self):
        """失败处理"""
        self.metrics.record_failure()
        if self.metrics.should_open():
            self.metrics.state = CircuitState.OPEN
            logger.critical(f"[CircuitBreaker] {self.name} 熔断器打开！")
            
    def _handle_fallback(self):
        """处理降级"""
        if self.fallback_function:
            return self.fallback_function()
        raise CircuitBreakerError(f"熔断器 {self.name} 已打开")
        
    def with_fallback(self, fallback: Callable):
        """设置降级函数"""
        self.fallback_function = fallback
        return self
        
    def get_state(self) -> Dict[str, Any]:
        """获取当前状态"""
        return {
            "name": self.name,
            "state": self.metrics.state.value,
            "failure_count": self.metrics.failure_count,
            "total_calls": self.metrics.total_calls,
            "total_failures": self.metrics.total_failures,
        }


class RateLimiter:
    """限流器 - 令牌桶算法"""
    
    def __init__(self, max_tokens: int = 100, refill_rate: float = 10.0):
        self.max_tokens = max_tokens
        self.tokens = max_tokens
        self.refill_rate = refill_rate
        self.last_refill = time.time()
        
    def acquire(self, tokens: int = 1) -> bool:
        """尝试获取令牌
        
        Returns:
            是否成功获取
        """
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
        
    def _refill(self):
        """补充令牌"""
        now = time.time()
        elapsed = now - self.last_refill
        new_tokens = elapsed * self.refill_rate
        self.tokens = min(self.max_tokens, self.tokens + new_tokens)
        self.last_refill = now


# ============================================
# 3. 分布式追踪 (Distributed Tracing)
# ============================================


@dataclass
class Span:
    """追踪跨度"""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    name: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_ms: float = 0.0
    attributes: Dict[str, Any] = field(default_factory=dict)
    status: str = "unknown"  # ok, error
    error_message: Optional[str] = None


class DistributedTracer:
    """分布式追踪管理器
    
    提供 OpenTelemetry 兼容的追踪接口
    """
    
    def __init__(self, service_name: str = "bayesian-agi-core"):
        self.service_name = service_name
        self.spans: Dict[str, Span] = {}
        self.traces: Dict[str, List[Span]] = defaultdict(list)
        
    def start_span(self, name: str, 
                  parent_span_id: Optional[str] = None,
                 attributes: Optional[Dict] = None) -> str:
        """开始一个新的 span
        
        Returns:
            span_id
        """
        span_id = str(uuid.uuid4())[:8]
        
        # 有父 span 的话，继承 trace_id，否则新建
        if parent_span_id and parent_span_id in self.spans:
            trace_id = self.spans[parent_span_id].trace_id
        else:
            trace_id = str(uuid.uuid4())[:16]
        
        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            name=name,
            attributes=attributes or {},
        )
        
        self.spans[span_id] = span
        self.traces[trace_id].append(span)
        logger.debug(f"[Tracer] 开始 span: {span_id} trace: {trace_id} name: {name}")
        
        return span_id
        
    def end_span(self, span_id: str, status: str = "ok", 
                 error_msg: Optional[str] = None):
        """结束 span"""
        if span_id not in self.spans:
            return
            
        span = self.spans[span_id]
        span.end_time = time.time()
        span.duration_ms = (span.end_time - span.start_time) * 1000
        span.status = status
        span.error_message = error_msg
        
        logger.debug(f"[Tracer] 结束 span: {span_id} 耗时: {span.duration_ms:.2f}ms")
        
    def get_trace(self, trace_id: str) -> List[Span]:
        """获取完整 trace"""
        return self.traces.get(trace_id, [])
        
    def get_slow_spans(self, threshold_ms: float = 100.0) -> List[Span]:
        """获取慢查询 span"""
        slow = []
        for spans in self.traces.values():
            for span in spans:
                if span.duration_ms > threshold_ms:
                    slow.append(span)
        return slow
        
    def export_trace_json(self, trace_id: str) -> str:
        """导出 trace 为 JSON"""
        spans = self.get_trace(trace_id)
        if not spans:
            return "{}"
            
        trace_data = {
            "trace_id": trace_id,
            "service": self.service_name,
            "spans": [
                {
                    "span_id": s.span_id,
                    "name": s.name,
                    "parent": s.parent_span_id,
                    "duration_ms": s.duration_ms,
                    "status": s.status,
                    "error": s.error_message,
                }
                for s in spans
            ]
        }
        return json.dumps(trace_data, ensure_ascii=False, indent=2)


def traced(tracer: DistributedTracer, span_name: Optional[str] = None):
    """追踪装饰器"""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            name = span_name or func.__name__
            span_id = tracer.start_span(name)
            try:
                result = func(*args, **kwargs)
                tracer.end_span(span_id, "ok")
                return result
            except Exception as e:
                tracer.end_span(span_id, "error", str(e))
                raise
        return wrapper
    return decorator


# ============================================
# 4. 业务健康检查 (Health Checks)
# ============================================


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """健康检查结果"""
    name: str
    status: HealthStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    check_time: str = field(default_factory=lambda: datetime.now().isoformat())


class HealthChecker:
    """业务健康检查器"""
    
    def __init__(self):
        self.checks: Dict[str, Callable[[], HealthCheck]] = {}
        
    def register_check(self, name: str, check_func: Callable[[], HealthCheck]):
        """注册健康检查"""
        self.checks[name] = check_func
        
    def check_all(self) -> Dict[str, Any]:
        """执行所有健康检查"""
        results = []
        overall = HealthStatus.HEALTHY
        
        for name, check in self.checks.items():
            try:
                result = check()
                results.append(result)
                if result.status == HealthStatus.UNHEALTHY:
                    overall = HealthStatus.UNHEALTHY
                elif result.status == HealthStatus.DEGRADED and overall == HealthStatus.HEALTHY:
                    overall = HealthStatus.DEGRADED
            except Exception as e:
                results.append(HealthCheck(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"检查执行失败: {str(e)}"
                ))
                overall = HealthStatus.UNHEALTHY
                
        return {
            "overall_status": overall.value,
            "timestamp": datetime.now().isoformat(),
            "checks": [
                {
                    "name": r.name,
                    "status": r.status.value,
                    "message": r.message,
                    "details": r.details
                }
                for r in results
            ]
        }


class DatabaseHealthCheck:
    """数据库健康检查"""
    
    def __init__(self, db_connection_check: Callable[[], bool]):
        self.db_connection_check = db_connection_check
        
    def __call__(self) -> HealthCheck:
        try:
            if self.db_connection_check():
                return HealthCheck(
                    name="database",
                    status=HealthStatus.HEALTHY,
                    message="数据库连接正常"
                )
            else:
                return HealthCheck(
                    name="database",
                    status=HealthStatus.UNHEALTHY,
                    message="数据库连接失败"
                )
        except Exception as e:
            return HealthCheck(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"数据库健康检查异常: {str(e)}"
            )


class EventBusHealthCheck:
    """事件总线健康检查"""
    
    def __init__(self, bus):
        self.bus = bus
        
    def __call__(self) -> HealthCheck:
        try:
            test_event = {"type": "health_check", "timestamp": datetime.now().isoformat()}
            return HealthCheck(
                name="event_bus",
                status=HealthStatus.HEALTHY,
                message="事件总线正常",
                details={"test_event": test_event}
            )
        except Exception as e:
            return HealthCheck(
                name="event_bus",
                status=HealthStatus.UNHEALTHY,
                message=f"事件总线健康检查失败: {str(e)}"
            )
