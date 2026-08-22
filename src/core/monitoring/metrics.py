#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能指标收集和监控系统
"""
import time
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Metric:
    """指标"""
    name: str
    value: Any
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: str = "gauge"  # gauge, counter, histogram


@dataclass
class PerformanceRecord:
    """性能记录"""
    operation: str
    start_time: float
    end_time: float
    duration: float
    success: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self.metrics: List[Metric] = []
        self.performance_records: List[PerformanceRecord] = []
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
    
    def increment_counter(self, name: str, labels: Optional[Dict[str, str]] = None, value: int = 1):
        """增加计数器"""
        self.counters[name] += value
        self.metrics.append(Metric(
            name=name,
            value=self.counters[name],
            labels=labels or {},
            metric_type="counter"
        ))
        logger.debug(f"Counter {name} incremented to {self.counters[name]}")
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """设置仪表值"""
        self.gauges[name] = value
        self.metrics.append(Metric(
            name=name,
            value=value,
            labels=labels or {},
            metric_type="gauge"
        ))
        logger.debug(f"Gauge {name} set to {value}")
    
    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """记录直方图数据"""
        self.histograms[name].append(value)
        self.metrics.append(Metric(
            name=name,
            value=value,
            labels=labels or {},
            metric_type="histogram"
        ))
    
    def measure_performance(self, operation: str, 
                          metadata: Optional[Dict[str, Any]] = None):
        """
        性能测量装饰器
        
        Args:
            operation: 操作名称
            metadata: 元数据
        """
        def decorator(func: Callable):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    raise
                finally:
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    record = PerformanceRecord(
                        operation=operation,
                        start_time=start_time,
                        end_time=end_time,
                        duration=duration,
                        success=success,
                        metadata=metadata or {}
                    )
                    self.performance_records.append(record)
                    
                    # 记录直方图和计数器
                    self.record_histogram(f"{operation}_duration", duration)
                    self.increment_counter(f"{operation}_total")
                    if success:
                        self.increment_counter(f"{operation}_success")
                    else:
                        self.increment_counter(f"{operation}_failure")
                    
                    logger.debug(f"Operation {operation} took {duration:.4f}s, success={success}")
            
            return wrapper
        return decorator
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "histograms": {},
            "performance": {}
        }
        
        # 计算直方图统计
        for name, values in self.histograms.items():
            if values:
                stats["histograms"][name] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "p50": sorted(values)[len(values) // 2] if len(values) > 0 else 0
                }
        
        # 计算性能统计
        operation_stats = defaultdict(lambda: {
            "count": 0,
            "total_duration": 0,
            "success_count": 0,
            "failure_count": 0
        })
        
        for record in self.performance_records:
            op_stats = operation_stats[record.operation]
            op_stats["count"] += 1
            op_stats["total_duration"] += record.duration
            if record.success:
                op_stats["success_count"] += 1
            else:
                op_stats["failure_count"] += 1
        
        for operation, op_stats in operation_stats.items():
            success_rate = op_stats["success_count"] / op_stats["count"] if op_stats["count"] > 0 else 0
            avg_duration = op_stats["total_duration"] / op_stats["count"] if op_stats["count"] > 0 else 0
            
            stats["performance"][operation] = {
                "count": op_stats["count"],
                "avg_duration": avg_duration,
                "success_rate": success_rate,
                "failure_count": op_stats["failure_count"]
            }
        
        return stats
    
    def export_prometheus_format(self) -> str:
        """导出为Prometheus格式"""
        lines = []
        
        # 导出计数器
        for name, value in self.counters.items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        
        # 导出仪表
        for name, value in self.gauges.items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")
        
        return "\n".join(lines)
    
    def reset(self):
        """重置所有指标"""
        self.metrics.clear()
        self.performance_records.clear()
        self.counters.clear()
        self.gauges.clear()
        self.histograms.clear()
        logger.info("Metrics reset")


# 全局指标收集器实例
_global_collector = None


def get_metrics_collector() -> MetricsCollector:
    """获取全局指标收集器"""
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricsCollector()
    return _global_collector
