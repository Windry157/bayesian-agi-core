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
        self.request_counter = Counter(
            "http_requests_total",
            "Total HTTP Requests",
            ["method", "endpoint", "status"],
        )
        self.request_duration = Histogram(
            "http_request_duration_seconds",
            "HTTP Request Duration",
            ["method", "endpoint"],
        )
        self.memory_usage = Gauge("memory_usage_bytes", "Memory Usage")
        self.cpu_usage = Gauge("cpu_usage_percent", "CPU Usage")
        self.model_inference_time = Summary(
            "model_inference_seconds", "Model Inference Time", ["model"]
        )
        self.memory_operations = Counter(
            "memory_operations_total", "Memory Operations", ["operation"]
        )
        # 新增：安全监控指标
        self.security_events = Counter(
            "security_events_total", "Security Events", ["type", "severity"]
        )
        self.constraint_violations = Counter(
            "constraint_violations_total", "Constraint Violations", ["type"]
        )
        # 新增：服务健康监控指标
        self.service_health = Gauge(
            "service_health_status", "Service Health Status", ["service"]
        )
        # 新增：系统性能指标
        self.system_load = Gauge("system_load", "System Load Average")
        self.disk_usage = Gauge("disk_usage_percent", "Disk Usage")
        # 新增：业务指标
        self.learning_cycles = Counter(
            "learning_cycles_total", "Learning Cycles", ["type"]
        )
        self.decision_making_time = Summary(
            "decision_making_seconds", "Decision Making Time"
        )

        # 异步指标
        self.registry = Registry()
        self.async_request_counter = AsyncCounter(
            "async_http_requests_total", "Total HTTP Requests"
        )
        self.async_request_duration = AsyncHistogram(
            "async_http_request_duration_seconds", "HTTP Request Duration"
        )
        # 新增：异步安全监控指标
        self.async_security_events = AsyncCounter(
            "async_security_events_total", "Security Events"
        )
        self.async_constraint_violations = AsyncCounter(
            "async_constraint_violations_total", "Constraint Violations"
        )
        # 新增：异步服务健康监控指标
        self.async_service_health = AsyncGauge(
            "async_service_health_status", "Service Health Status"
        )
        # 新增：异步业务指标
        self.async_learning_cycles = AsyncCounter(
            "async_learning_cycles_total", "Learning Cycles"
        )

        # 注册异步指标
        self.registry.register(self.async_request_counter)
        self.registry.register(self.async_request_duration)
        self.registry.register(self.async_security_events)
        self.registry.register(self.async_constraint_violations)
        self.registry.register(self.async_service_health)
        self.registry.register(self.async_learning_cycles)

    def record_request(self, method: str, endpoint: str, status: int, duration: float):
        """记录HTTP请求

        Args:
            method: HTTP方法
            endpoint: 端点
            status: 状态码
            duration: 持续时间
        """
        self.request_counter.labels(
            method=method, endpoint=endpoint, status=status
        ).inc()
        self.request_duration.labels(method=method, endpoint=endpoint).observe(duration)

    async def async_record_request(
        self, method: str, endpoint: str, status: int, duration: float
    ):
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

    def record_security_event(self, event_type: str, severity: str):
        """记录安全事件

        Args:
            event_type: 事件类型
            severity: 严重程度
        """
        self.security_events.labels(type=event_type, severity=severity).inc()

    def record_constraint_violation(self, violation_type: str):
        """记录约束违反

        Args:
            violation_type: 违反类型
        """
        self.constraint_violations.labels(type=violation_type).inc()

    def record_service_health(self, service: str, status: float):
        """记录服务健康状态

        Args:
            service: 服务名称
            status: 健康状态（1=健康，0=不健康）
        """
        self.service_health.labels(service=service).set(status)

    def record_system_load(self, load: float):
        """记录系统负载

        Args:
            load: 系统负载
        """
        self.system_load.set(load)

    def record_disk_usage(self, usage: float):
        """记录磁盘使用情况

        Args:
            usage: 磁盘使用率（百分比）
        """
        self.disk_usage.set(usage)

    def record_learning_cycle(self, cycle_type: str):
        """记录学习周期

        Args:
            cycle_type: 学习周期类型
        """
        self.learning_cycles.labels(type=cycle_type).inc()

    def record_decision_making(self, duration: float):
        """记录决策制定时间

        Args:
            duration: 决策制定时间（秒）
        """
        self.decision_making_time.observe(duration)

    async def async_record_security_event(self, event_type: str, severity: str):
        """异步记录安全事件

        Args:
            event_type: 事件类型
            severity: 严重程度
        """
        await self.async_security_events.inc()

    async def async_record_constraint_violation(self, violation_type: str):
        """异步记录约束违反

        Args:
            violation_type: 违反类型
        """
        await self.async_constraint_violations.inc()

    async def async_record_service_health(self, service: str, status: float):
        """异步记录服务健康状态

        Args:
            service: 服务名称
            status: 健康状态（1=健康，0=不健康）
        """
        await self.async_service_health.set(status)

    async def async_record_learning_cycle(self, cycle_type: str):
        """异步记录学习周期

        Args:
            cycle_type: 学习周期类型
        """
        await self.async_learning_cycles.inc()

    async def get_metrics(self):
        """获取指标

        Returns:
            指标数据
        """
        # 使用text格式渲染指标
        content = await render(self.registry, format="text")
        return content, {"Content-Type": "text/plain; version=0.0.4"}


# 创建监控系统实例
monitoring = MonitoringSystem()
