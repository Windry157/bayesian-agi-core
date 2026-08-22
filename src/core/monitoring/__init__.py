"""
监控模块 - 提供系统监控、指标收集和告警功能
"""
import time
import logging
from .metrics_collector import MetricsCollector
from .alerts import AlertManager, AlertRule, AlertSeverity
from .system_monitor import SystemMonitor
from .dashboard import MonitoringDashboard, get_dashboard
from .metrics import MetricsCollector as PerformanceMetricsCollector, get_metrics_collector

logger = logging.getLogger(__name__)


class _MonitoringSystem:
    """系统监控单例 - 提供中间件和API使用的监控接口"""

    def __init__(self):
        self.metrics = get_metrics_collector()
        self.system_monitor = SystemMonitor()
        self.start_time = time.time()

    def record_request(self, method: str, endpoint: str, status: int, duration: float):
        self.metrics.increment_counter("http_requests_total", labels={"method": method, "endpoint": endpoint, "status": str(status)})
        self.metrics.record_histogram("http_request_duration_seconds", duration, labels={"method": method, "endpoint": endpoint})

    def record_memory_usage(self, usage: float):
        self.metrics.set_gauge("memory_usage_bytes", usage)

    def record_cpu_usage(self, usage: float):
        self.metrics.set_gauge("cpu_usage_percent", usage)

    def get_uptime(self) -> float:
        return time.time() - self.start_time


monitoring = _MonitoringSystem()

__all__ = [
    'MetricsCollector', 
    'AlertManager', 
    'AlertRule', 
    'AlertSeverity', 
    'SystemMonitor',
    'MonitoringDashboard',
    'get_dashboard',
    'PerformanceMetricsCollector',
    'get_metrics_collector',
    'monitoring',
]
