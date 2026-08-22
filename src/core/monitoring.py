#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控系统模块
集成Prometheus和Grafana
"""

import time
from prometheus_client import Counter, Gauge, Histogram, Summary


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


# 创建监控系统实例
monitoring = MonitoringSystem()
