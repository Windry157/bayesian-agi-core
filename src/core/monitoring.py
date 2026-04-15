#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控系统模块
集成Prometheus和Grafana
"""

import time
from prometheus_client import Counter, Gauge, Histogram, Summary
from aioprometheus import Counter as AsyncCounter
from aioprometheus import Gauge as AsyncGauge
from aioprometheus import Histogram as AsyncHistogram
from aioprometheus import Summary as AsyncSummary
from aioprometheus import Registry, render


class MonitoringSystem:
    """监控系统
    
    集成Prometheus和Grafana，提供系统监控功能
    """
    
    def __init__(self):
        """初始化监控系统"""
        # 同步指标
        self.request_counter = Counter('http_requests_total', 'Total HTTP Requests', ['method', 'endpoint', 'status'])
        self.request_duration = Histogram('http_request_duration_seconds', 'HTTP Request Duration', ['method', 'endpoint'])
        self.memory_usage = Gauge('memory_usage_bytes', 'Memory Usage')
        self.cpu_usage = Gauge('cpu_usage_percent', 'CPU Usage')
        self.model_inference_time = Summary('model_inference_seconds', 'Model Inference Time', ['model'])
        self.memory_operations = Counter('memory_operations_total', 'Memory Operations', ['operation'])
        
        # 异步指标
        self.registry = Registry()
        self.async_request_counter = AsyncCounter('async_http_requests_total', 'Total HTTP Requests')
        self.async_request_duration = AsyncHistogram('async_http_request_duration_seconds', 'HTTP Request Duration')
        
        # 注册异步指标
        self.registry.register(self.async_request_counter)
        self.registry.register(self.async_request_duration)
    
    def record_request(self, method: str, endpoint: str, status: int, duration: float):
        """记录HTTP请求
        
        Args:
            method: HTTP方法
            endpoint: 端点
            status: 状态码
            duration: 持续时间
        """
        self.request_counter.labels(method=method, endpoint=endpoint, status=status).inc()
        self.request_duration.labels(method=method, endpoint=endpoint).observe(duration)
    
    async def async_record_request(self, method: str, endpoint: str, status: int, duration: float):
        """异步记录HTTP请求
        
        Args:
            method: HTTP方法
            endpoint: 端点
            status: 状态码
            duration: 持续时间
        """
        await self.async_request_counter.inc()
        await self.async_request_duration.observe(duration)
    
    def record_memory_usage(self, usage: float):
        """记录内存使用情况
        
        Args:
            usage: 内存使用量（字节）
        """
        self.memory_usage.set(usage)
    
    def record_cpu_usage(self, usage: float):
        """记录CPU使用情况
        
        Args:
            usage: CPU使用率（百分比）
        """
        self.cpu_usage.set(usage)
    
    def record_model_inference(self, model: str, duration: float):
        """记录模型推理时间
        
        Args:
            model: 模型名称
            duration: 推理时间（秒）
        """
        self.model_inference_time.labels(model=model).observe(duration)
    
    def record_memory_operation(self, operation: str):
        """记录内存操作
        
        Args:
            operation: 操作类型
        """
        self.memory_operations.labels(operation=operation).inc()
    
    async def get_metrics(self):
        """获取指标
        
        Returns:
            指标数据
        """
        # 使用text格式渲染指标
        content = await render(self.registry, format='text')
        return content, {"Content-Type": "text/plain; version=0.0.4"}


# 创建监控系统实例
monitoring = MonitoringSystem()
