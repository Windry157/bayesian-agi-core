#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenTelemetry 分布式链路追踪模块
实现端到端的请求追踪能力
"""

import logging
from typing import Optional, Dict, Any
from contextvars import ContextVar

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.trace import SpanKind, StatusCode
    from opentelemetry.attributes import BoundedAttributes
    HAS_OPENTELEMETRY = True
    logger.info("OpenTelemetry 已加载")
except ImportError:
    HAS_OPENTELEMETRY = False
    logger.warning("OpenTelemetry 未安装，将使用模拟实现")
    
    class SpanKind:
        INTERNAL = "INTERNAL"
        SERVER = "SERVER"
        CLIENT = "CLIENT"
        PRODUCER = "PRODUCER"
        CONSUMER = "CONSUMER"

# 当前Span上下文
_current_span = ContextVar("current_span", default=None)


class Tracer:
    """分布式链路追踪器"""
    
    def __init__(self, service_name: str = "bayesian-agi-core"):
        self.service_name = service_name
        self._tracer = None
        
        if HAS_OPENTELEMETRY:
            resource = Resource.create({"service.name": service_name})
            provider = TracerProvider(resource=resource)
            processor = BatchSpanProcessor(ConsoleSpanExporter())
            provider.add_span_processor(processor)
            trace.set_tracer_provider(provider)
            self._tracer = trace.get_tracer(service_name)
    
    def start_span(self, name: str, kind: SpanKind = SpanKind.INTERNAL, attributes: Optional[Dict[str, Any]] = None):
        """启动一个新的Span"""
        if HAS_OPENTELEMETRY and self._tracer:
            span = self._tracer.start_span(name, kind=kind)
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
            _current_span.set(span)
            return SpanWrapper(span)
        else:
            # 模拟实现
            return MockSpan(name, attributes)
    
    def get_current_span(self):
        """获取当前Span"""
        return _current_span.get()


class SpanWrapper:
    """Span包装器"""
    
    def __init__(self, span):
        self._span = span
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self._span.set_status(StatusCode.ERROR, str(exc_val))
        self._span.end()
    
    def set_attribute(self, key: str, value: Any):
        """设置Span属性"""
        self._span.set_attribute(key, value)
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """添加事件"""
        self._span.add_event(name, attributes=attributes)
    
    def end(self):
        """结束Span"""
        self._span.end()


class MockSpan:
    """模拟Span实现（当OpenTelemetry不可用时）"""
    
    def __init__(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        self.name = name
        self.attributes = attributes or {}
        self.start_time = __import__('time').time()
        self.events = []
    
    def __enter__(self):
        logger.debug(f"开始Span: {self.name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (__import__('time').time() - self.start_time) * 1000
        if exc_type:
            logger.debug(f"Span {self.name} 失败: {exc_val}")
        else:
            logger.debug(f"Span {self.name} 完成，耗时: {duration:.2f}ms")
    
    def set_attribute(self, key: str, value: Any):
        self.attributes[key] = value
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        self.events.append({"name": name, "attributes": attributes})
    
    def end(self):
        duration = (__import__('time').time() - self.start_time) * 1000
        logger.debug(f"Span {self.name} 结束，耗时: {duration:.2f}ms")


# 全局追踪器实例
tracer = Tracer("bayesian-agi-core")


def trace_method(name: Optional[str] = None):
    """装饰器：为方法添加追踪"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            span_name = name or func.__name__
            with tracer.start_span(span_name):
                return await func(*args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            span_name = name or func.__name__
            with tracer.start_span(span_name):
                return func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator
