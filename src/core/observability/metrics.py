#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能指标监控模块
实现 P95/P99 延迟监控、吞吐量统计等核心指标
"""

import logging
import time
import statistics
from typing import Dict, List, Optional, Any
from collections import deque
from threading import Lock

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class LatencyTracker:
    """延迟追踪器，支持 P95/P99 计算"""
    
    def __init__(self, window_size: int = 1000):
        """
        初始化延迟追踪器
        
        Args:
            window_size: 滑动窗口大小，用于计算百分位数
        """
        self.window_size = window_size
        self.latencies = deque(maxlen=window_size)
        self.lock = Lock()
    
    def record(self, latency_ms: float):
        """记录延迟（毫秒）"""
        with self.lock:
            self.latencies.append(latency_ms)
    
    def get_percentiles(self) -> Dict[str, float]:
        """获取延迟百分位数"""
        with self.lock:
            if not self.latencies:
                return {
                    "p50": 0.0,
                    "p90": 0.0,
                    "p95": 0.0,
                    "p99": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "avg": 0.0,
                    "count": 0
                }
            
            sorted_latencies = sorted(self.latencies)
            n = len(sorted_latencies)
            
            return {
                "p50": self._percentile(sorted_latencies, 50),
                "p90": self._percentile(sorted_latencies, 90),
                "p95": self._percentile(sorted_latencies, 95),
                "p99": self._percentile(sorted_latencies, 99),
                "min": sorted_latencies[0],
                "max": sorted_latencies[-1],
                "avg": sum(self.latencies) / n,
                "count": n
            }
    
    def _percentile(self, sorted_data: List[float], percentile: int) -> float:
        """计算百分位数"""
        n = len(sorted_data)
        if n == 0:
            return 0.0
        
        index = (percentile / 100.0) * (n - 1)
        lower = int(index)
        upper = min(lower + 1, n - 1)
        fraction = index - lower
        
        return sorted_data[lower] + fraction * (sorted_data[upper] - sorted_data[lower])


class ThroughputTracker:
    """吞吐量追踪器"""
    
    def __init__(self, window_seconds: int = 60):
        """
        初始化吞吐量追踪器
        
        Args:
            window_seconds: 时间窗口大小（秒）
        """
        self.window_seconds = window_seconds
        self.timestamps = deque()
        self.lock = Lock()
    
    def record(self):
        """记录一次请求"""
        with self.lock:
            now = time.time()
            self.timestamps.append(now)
            # 移除窗口外的记录
            cutoff = now - self.window_seconds
            while self.timestamps and self.timestamps[0] < cutoff:
                self.timestamps.popleft()
    
    def get_throughput(self) -> float:
        """获取当前吞吐量（请求/秒）"""
        with self.lock:
            if not self.timestamps:
                return 0.0
            return len(self.timestamps) / self.window_seconds


class MetricsCollector:
    """指标收集器，聚合所有监控指标"""
    
    def __init__(self):
        self.latency_trackers: Dict[str, LatencyTracker] = {}
        self.throughput_trackers: Dict[str, ThroughputTracker] = {}
        self.counters: Dict[str, int] = {}
        self.gauges: Dict[str, float] = {}
        self.lock = Lock()
    
    def get_or_create_latency_tracker(self, name: str) -> LatencyTracker:
        """获取或创建延迟追踪器"""
        with self.lock:
            if name not in self.latency_trackers:
                self.latency_trackers[name] = LatencyTracker()
            return self.latency_trackers[name]
    
    def get_or_create_throughput_tracker(self, name: str) -> ThroughputTracker:
        """获取或创建吞吐量追踪器"""
        with self.lock:
            if name not in self.throughput_trackers:
                self.throughput_trackers[name] = ThroughputTracker()
            return self.throughput_trackers[name]
    
    def increment_counter(self, name: str, delta: int = 1):
        """增加计数器"""
        with self.lock:
            self.counters[name] = self.counters.get(name, 0) + delta
    
    def set_gauge(self, name: str, value: float):
        """设置仪表盘值"""
        with self.lock:
            self.gauges[name] = value
    
    def record_latency(self, name: str, latency_ms: float):
        """记录延迟"""
        tracker = self.get_or_create_latency_tracker(name)
        tracker.record(latency_ms)
    
    def record_request(self, name: str):
        """记录请求"""
        tracker = self.get_or_create_throughput_tracker(name)
        tracker.record()
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        metrics = {}
        
        # 延迟指标
        for name, tracker in self.latency_trackers.items():
            metrics[f"latency_{name}"] = tracker.get_percentiles()
        
        # 吞吐量指标
        for name, tracker in self.throughput_trackers.items():
            metrics[f"throughput_{name}"] = {
                "req_per_sec": tracker.get_throughput()
            }
        
        # 计数器
        metrics["counters"] = self.counters.copy()
        
        # 仪表盘
        metrics["gauges"] = self.gauges.copy()
        
        return metrics
    
    def reset(self):
        """重置所有指标"""
        with self.lock:
            self.latency_trackers.clear()
            self.throughput_trackers.clear()
            self.counters.clear()
            self.gauges.clear()


# 全局指标收集器实例
metrics_collector = MetricsCollector()


def monitor_latency(name: str):
    """装饰器：监控方法延迟"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                latency_ms = (time.time() - start) * 1000
                metrics_collector.record_latency(name, latency_ms)
                metrics_collector.record_request(name)
        
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                latency_ms = (time.time() - start) * 1000
                metrics_collector.record_latency(name, latency_ms)
                metrics_collector.record_request(name)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


def print_metrics_summary():
    """打印指标摘要"""
    metrics = metrics_collector.get_metrics()
    logger.info("=== 性能指标摘要 ===")
    
    for key, value in metrics.items():
        if key.startswith("latency_"):
            logger.info(f"{key}:")
            logger.info(f"  P50: {value['p50']:.2f}ms")
            logger.info(f"  P90: {value['p90']:.2f}ms")
            logger.info(f"  P95: {value['p95']:.2f}ms")
            logger.info(f"  P99: {value['p99']:.2f}ms")
            logger.info(f"  Min/Max/Avg: {value['min']:.2f}ms / {value['max']:.2f}ms / {value['avg']:.2f}ms")
            logger.info(f"  样本数: {value['count']}")
        elif key.startswith("throughput_"):
            logger.info(f"{key}: {value['req_per_sec']:.2f} req/s")
        elif key == "counters":
            logger.info(f"计数器: {value}")
        elif key == "gauges":
            logger.info(f"仪表盘: {value}")


if __name__ == "__main__":
    # 示例用法
    import asyncio
    
    @monitor_latency("test_operation")
    async def test_operation(delay_ms: int):
        await asyncio.sleep(delay_ms / 1000)
        return "done"
    
    async def main():
        # 模拟一些请求
        for i in range(100):
            delay = int(10 + (i % 10) * 5)  # 10-55ms
            await test_operation(delay)
        
        print_metrics_summary()
    
    asyncio.run(main())
