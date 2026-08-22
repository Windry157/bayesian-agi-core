#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prometheus Metrics Exporter
Prometheus 指标导出器
"""

from typing import Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class Metric:
    """指标数据"""
    name: str
    value: float
    type: str = "gauge"  # gauge, counter, histogram
    labels: Dict[str, str] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = {}
        if self.timestamp is None:
            self.timestamp = datetime.now().timestamp()


class MetricsRegistry:
    """指标注册表"""
    
    def __init__(self):
        self.metrics: Dict[str, Metric] = {}
        self.counters: Dict[str, float] = {}
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """设置 Gauge 类型指标"""
        self.metrics[name] = Metric(
            name=name,
            value=value,
            type="gauge",
            labels=labels
        )
    
    def increment_counter(self, name: str, amount: float = 1.0, labels: Dict[str, str] = None):
        """增加计数器"""
        if name not in self.counters:
            self.counters[name] = 0.0
        
        self.counters[name] += amount
        
        self.metrics[name] = Metric(
            name=name,
            value=self.counters[name],
            type="counter",
            labels=labels
        )
    
    def increment_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """记录直方图数据（简化版）"""
        self.metrics[name] = Metric(
            name=name,
            value=value,
            type="histogram",
            labels=labels
        )
    
    def reset_counter(self, name: str):
        """重置计数器"""
        if name in self.counters:
            self.counters[name] = 0.0
    
    def export(self) -> str:
        """导出 Prometheus 格式"""
        lines = []
        for name, metric in self.metrics.items():
            # 构建 HELP 和 TYPE 行
            lines.append(f"# HELP {name} {name} metric")
            lines.append(f"# TYPE {name} {metric.type}")
            
            # 构建指标行
            label_str = ""
            if metric.labels:
                label_parts = [f'{k}="{v}"' for k, v in metric.labels.items()]
                label_str = "{" + ",".join(label_parts) + "}"
            
            line = f"{name}{label_str} {metric.value} {int(metric.timestamp * 1000)}"
            lines.append(line)
        
        return "\n".join(lines)


# 全局指标注册表
_metrics_registry = MetricsRegistry()


def get_metrics_registry() -> MetricsRegistry:
    """获取全局指标注册表"""
    return _metrics_registry


# 快捷函数
def record_circuit_breaker_state(name: str, state: str, failure_count: int = 0):
    """记录熔断器状态"""
    registry = get_metrics_registry()
    
    state_mapping = {
        "CLOSED": 0,
        "OPEN": 1,
        "HALF_OPEN": 2
    }
    
    registry.set_gauge(
        "circuit_breaker_state",
        state_mapping.get(state, 0),
        {"circuit_name": name}
    )
    
    registry.set_gauge(
        "circuit_breaker_failure_count",
        failure_count,
        {"circuit_name": name}
    )


def record_rate_limit_hit(name: str, allowed: bool):
    """记录限流事件"""
    registry = get_metrics_registry()
    
    if allowed:
        registry.increment_counter(
            "rate_limit_allowed",
            1.0,
            {"limiter_name": name}
        )
    else:
        registry.increment_counter(
            "rate_limit_rejected",
            1.0,
            {"limiter_name": name}
        )


def record_request_duration(duration_seconds: float, endpoint: str, status_code: int):
    """记录请求耗时"""
    registry = get_metrics_registry()
    registry.increment_histogram(
        "request_duration_seconds",
        duration_seconds,
        {"endpoint": endpoint, "status_code": str(status_code)}
    )


def record_error(error_type: str, endpoint: str):
    """记录错误"""
    registry = get_metrics_registry()
    registry.increment_counter(
        "error_count",
        1.0,
        {"error_type": error_type, "endpoint": endpoint}
    )
