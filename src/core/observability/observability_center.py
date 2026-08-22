#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可观测性监控中心
整合全链路追踪、成本监控、告警系统和指标导出

核心功能：
1. 全链路分布式追踪
2. 成本监控（Token消耗、计算时长）
3. 性能指标（P95/P99延迟、吞吐量）
4. 告警系统
5. Prometheus指标导出
"""

import logging
import time
import statistics
from typing import Dict, List, Optional, Any, Callable
from collections import deque
from threading import Lock
from datetime import datetime
import json
import os
from enum import Enum
from dataclasses import dataclass, field

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ==================== 成本监控模块 ====================

class CostTracker:
    """成本追踪器 - 追踪Token消耗和计算资源"""
    
    def __init__(self):
        self.token_usage = deque(maxlen=1000)  # 最近1000次Token消耗记录
        self.compute_time = deque(maxlen=1000)  # 计算时长记录（毫秒）
        self.lock = Lock()
        self.rates = {
            "input_token_cost": 0.002,   # $0.002 per 1K tokens
            "output_token_cost": 0.006,  # $0.006 per 1K tokens
            "compute_cost": 0.01,        # $0.01 per 1000ms compute time
        }
    
    def record_token_usage(self, input_tokens: int, output_tokens: int):
        """记录Token使用量"""
        with self.lock:
            self.token_usage.append({
                "timestamp": time.time(),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens
            })
    
    def record_compute_time(self, duration_ms: float):
        """记录计算时长"""
        with self.lock:
            self.compute_time.append({
                "timestamp": time.time(),
                "duration_ms": duration_ms
            })
    
    def get_cost_summary(self) -> Dict[str, float]:
        """获取成本摘要"""
        with self.lock:
            if not self.token_usage and not self.compute_time:
                return {
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                    "total_tokens": 0,
                    "token_cost_usd": 0.0,
                    "total_compute_ms": 0.0,
                    "compute_cost_usd": 0.0,
                    "total_cost_usd": 0.0,
                    "avg_tokens_per_request": 0.0,
                    "avg_compute_ms_per_request": 0.0
                }
            
            # Token统计
            total_input = sum(r["input_tokens"] for r in self.token_usage)
            total_output = sum(r["output_tokens"] for r in self.token_usage)
            total_tokens = total_input + total_output
            
            # 成本计算
            token_cost = (total_input * self.rates["input_token_cost"] + 
                         total_output * self.rates["output_token_cost"]) / 1000
            
            # 计算时长统计
            total_compute = sum(r["duration_ms"] for r in self.compute_time)
            compute_cost = (total_compute / 1000) * self.rates["compute_cost"]
            
            return {
                "total_input_tokens": total_input,
                "total_output_tokens": total_output,
                "total_tokens": total_tokens,
                "token_cost_usd": round(token_cost, 4),
                "total_compute_ms": round(total_compute, 2),
                "compute_cost_usd": round(compute_cost, 4),
                "total_cost_usd": round(token_cost + compute_cost, 4),
                "avg_tokens_per_request": round(total_tokens / len(self.token_usage), 1) if self.token_usage else 0.0,
                "avg_compute_ms_per_request": round(total_compute / len(self.compute_time), 2) if self.compute_time else 0.0
            }
    
    def set_rates(self, input_token_cost: float, output_token_cost: float, compute_cost: float):
        """设置成本费率"""
        with self.lock:
            self.rates["input_token_cost"] = input_token_cost
            self.rates["output_token_cost"] = output_token_cost
            self.rates["compute_cost"] = compute_cost


# ==================== 告警系统 ====================

class AlertSeverity(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """告警对象"""
    id: str
    severity: AlertSeverity
    title: str
    message: str
    timestamp: float
    resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class AlertManager:
    """告警管理器"""
    
    def __init__(self):
        self.alerts: List[Alert] = []
        self.lock = Lock()
        self.alert_handlers: List[Callable[[Alert], None]] = []
        
        # 默认告警规则
        self.rules = {
            "high_latency": {
                "threshold": 5000,  # 5秒
                "severity": AlertSeverity.CRITICAL,
                "description": "高延迟告警"
            },
            "high_error_rate": {
                "threshold": 0.1,  # 10%错误率
                "severity": AlertSeverity.WARNING,
                "description": "高错误率告警"
            },
            "rate_limit_exceeded": {
                "threshold": 0,
                "severity": AlertSeverity.WARNING,
                "description": "速率限制超限"
            },
            "circuit_breaker_open": {
                "threshold": 0,
                "severity": AlertSeverity.CRITICAL,
                "description": "熔断器打开"
            },
            "high_cost": {
                "threshold": 10.0,  # $10
                "severity": AlertSeverity.WARNING,
                "description": "高成本告警"
            }
        }
    
    def add_handler(self, handler: Callable[[Alert], None]):
        """添加告警处理器"""
        with self.lock:
            self.alert_handlers.append(handler)
    
    def trigger_alert(self, rule_name: str, message: str, **metadata):
        """触发告警"""
        if rule_name not in self.rules:
            logger.warning(f"未知的告警规则: {rule_name}")
            return
        
        rule = self.rules[rule_name]
        alert = Alert(
            id=f"{rule_name}-{int(time.time())}",
            severity=rule["severity"],
            title=rule["description"],
            message=message,
            timestamp=time.time(),
            metadata=metadata
        )
        
        with self.lock:
            self.alerts.append(alert)
        
        # 通知所有处理器
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"告警处理器执行失败: {e}")
        
        logger.warning(f"[ALERT] [{alert.severity.value.upper()}] {alert.title}: {alert.message}")
    
    def resolve_alert(self, alert_id: str):
        """解决告警"""
        with self.lock:
            for alert in self.alerts:
                if alert.id == alert_id:
                    alert.resolved = True
                    logger.info(f"告警已解决: {alert_id}")
                    return True
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活动告警"""
        with self.lock:
            return [a for a in self.alerts if not a.resolved]
    
    def get_alerts_by_severity(self, severity: AlertSeverity) -> List[Alert]:
        """按级别获取告警"""
        with self.lock:
            return [a for a in self.alerts if a.severity == severity and not a.resolved]


# ==================== Prometheus 指标导出 ====================

class PrometheusExporter:
    """Prometheus指标导出器"""
    
    def __init__(self):
        self.metrics = {}
        self.lock = Lock()
    
    def add_counter(self, name: str, value: int, labels: Optional[Dict[str, str]] = None):
        """添加计数器指标"""
        key = self._make_key(name, labels)
        with self.lock:
            if key not in self.metrics:
                self.metrics[key] = {
                    "type": "counter",
                    "value": 0,
                    "labels": labels or {},
                    "help": f"Counter for {name}"
                }
            self.metrics[key]["value"] += value
    
    def add_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """添加仪表盘指标"""
        key = self._make_key(name, labels)
        with self.lock:
            self.metrics[key] = {
                "type": "gauge",
                "value": value,
                "labels": labels or {},
                "help": f"Gauge for {name}"
            }
    
    def add_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """添加直方图指标"""
        key = self._make_key(name, labels)
        with self.lock:
            if key not in self.metrics:
                self.metrics[key] = {
                    "type": "histogram",
                    "values": [],
                    "labels": labels or {},
                    "help": f"Histogram for {name}"
                }
            self.metrics[key]["values"].append(value)
            # 保持最多1000个样本
            if len(self.metrics[key]["values"]) > 1000:
                self.metrics[key]["values"].pop(0)
    
    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """生成指标键"""
        label_str = ",".join(f"{k}={v}" for k, v in sorted((labels or {}).items()))
        return f"{name}|{label_str}"
    
    def generate_metrics_text(self) -> str:
        """生成Prometheus格式的指标文本"""
        lines = []
        
        with self.lock:
            for key, metric in self.metrics.items():
                name = key.split("|")[0]
                labels = metric["labels"]
                
                # 生成标签字符串
                if labels:
                    label_parts = [f'{k}="{v}"' for k, v in labels.items()]
                    label_str = "{" + ",".join(label_parts) + "}"
                else:
                    label_str = ""
                
                # 添加帮助信息
                lines.append(f"# HELP {name} {metric['help']}")
                lines.append(f"# TYPE {name} {metric['type']}")
                
                # 添加指标值
                if metric["type"] == "counter" or metric["type"] == "gauge":
                    lines.append(f"{name}{label_str} {metric['value']}")
                elif metric["type"] == "histogram":
                    values = metric["values"]
                    if values:
                        # 计算汇总统计
                        count = len(values)
                        sum_val = sum(values)
                        lines.append(f"{name}_count{label_str} {count}")
                        lines.append(f"{name}_sum{label_str} {sum_val}")
                        
                        # 百分位数
                        sorted_vals = sorted(values)
                        p50 = self._percentile(sorted_vals, 50)
                        p90 = self._percentile(sorted_vals, 90)
                        p95 = self._percentile(sorted_vals, 95)
                        p99 = self._percentile(sorted_vals, 99)
                        
                        lines.append(f"{name}_bucket{label_str},le=0.5 {sum(1 for v in values if v <= 0.5)}")
                        lines.append(f"{name}_bucket{label_str},le=1.0 {sum(1 for v in values if v <= 1.0)}")
                        lines.append(f"{name}_bucket{label_str},le=5.0 {sum(1 for v in values if v <= 5.0)}")
                        lines.append(f"{name}_bucket{label_str},le=10.0 {sum(1 for v in values if v <= 10.0)}")
                        lines.append(f"{name}_bucket{label_str},le=+Inf {count}")
        
        return "\n".join(lines) + "\n"
    
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


# ==================== 日志聚合器 ====================

class LogEntry:
    """日志条目"""
    def __init__(self, timestamp: float, level: str, message: str, context: Dict[str, Any]):
        self.timestamp = timestamp
        self.level = level
        self.message = message
        self.context = context


class LogAggregator:
    """日志聚合器"""
    
    def __init__(self, max_entries: int = 10000):
        self.entries = deque(maxlen=max_entries)
        self.lock = Lock()
        self.error_count = 0
        self.warning_count = 0
    
    def add_entry(self, level: str, message: str, **context):
        """添加日志条目"""
        entry = LogEntry(
            timestamp=time.time(),
            level=level.upper(),
            message=message,
            context=context
        )
        
        with self.lock:
            self.entries.append(entry)
            if level.upper() == "ERROR":
                self.error_count += 1
            elif level.upper() == "WARNING":
                self.warning_count += 1
    
    def get_recent_errors(self, limit: int = 10) -> List[LogEntry]:
        """获取最近的错误日志"""
        with self.lock:
            errors = [e for e in self.entries if e.level == "ERROR"]
            return errors[-limit:]
    
    def get_recent_entries(self, limit: int = 50) -> List[LogEntry]:
        """获取最近的日志条目"""
        with self.lock:
            return list(self.entries)[-limit:]
    
    def get_error_rate(self, window_seconds: int = 60) -> float:
        """获取错误率"""
        with self.lock:
            now = time.time()
            window_entries = [e for e in self.entries if now - e.timestamp < window_seconds]
            if not window_entries:
                return 0.0
            error_count = sum(1 for e in window_entries if e.level == "ERROR")
            return error_count / len(window_entries)
    
    def export_to_file(self, filepath: str):
        """导出日志到文件"""
        with self.lock:
            data = [{
                "timestamp": e.timestamp,
                "level": e.level,
                "message": e.message,
                "context": e.context
            } for e in self.entries]
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# ==================== 监控中心 ====================

class ObservabilityCenter:
    """可观测性监控中心 - 整合所有监控功能"""
    
    def __init__(self):
        # 初始化子模块
        from src.core.observability.tracing import tracer
        from src.core.observability.metrics import metrics_collector
        
        self.tracer = tracer
        self.metrics = metrics_collector
        self.cost_tracker = CostTracker()
        self.alert_manager = AlertManager()
        self.prometheus_exporter = PrometheusExporter()
        self.log_aggregator = LogAggregator()
        
        # 设置默认告警处理器
        self._setup_default_handlers()
        
        logger.info("可观测性监控中心初始化完成")
    
    def _setup_default_handlers(self):
        """设置默认告警处理器"""
        # 日志告警处理器
        def log_alert_handler(alert: Alert):
            logger.error(f"[ALERT] [{alert.severity.value}] {alert.title}: {alert.message}")
        
        self.alert_manager.add_handler(log_alert_handler)
    
    def record_token_usage(self, input_tokens: int, output_tokens: int):
        """记录Token使用量"""
        self.cost_tracker.record_token_usage(input_tokens, output_tokens)
        self.prometheus_exporter.add_counter("llm_tokens_input", input_tokens)
        self.prometheus_exporter.add_counter("llm_tokens_output", output_tokens)
    
    def record_compute_time(self, duration_ms: float):
        """记录计算时长"""
        self.cost_tracker.record_compute_time(duration_ms)
        self.prometheus_exporter.add_histogram("compute_duration_seconds", duration_ms / 1000)
    
    def record_latency(self, operation: str, latency_ms: float):
        """记录操作延迟"""
        self.metrics.record_latency(operation, latency_ms)
        self.prometheus_exporter.add_histogram(f"{operation}_latency_seconds", latency_ms / 1000)
        
        # 检查高延迟告警
        if latency_ms > 5000:
            self.alert_manager.trigger_alert(
                "high_latency",
                f"{operation} 延迟过高: {latency_ms:.2f}ms",
                operation=operation,
                latency_ms=latency_ms
            )
    
    def record_request(self, operation: str):
        """记录请求"""
        self.metrics.record_request(operation)
        self.prometheus_exporter.add_counter(f"{operation}_requests", 1)
    
    def record_error(self, operation: str, error: Exception):
        """记录错误"""
        self.metrics.increment_counter(f"{operation}_errors")
        self.prometheus_exporter.add_counter(f"{operation}_errors", 1)
        self.log_aggregator.add_entry("error", str(error), operation=operation)
        
        # 检查错误率
        error_rate = self.log_aggregator.get_error_rate()
        if error_rate > 0.1:
            self.alert_manager.trigger_alert(
                "high_error_rate",
                f"{operation} 错误率过高: {error_rate:.2%}",
                operation=operation,
                error_rate=error_rate
            )
    
    def log_info(self, message: str, **context):
        """记录信息日志"""
        self.log_aggregator.add_entry("info", message, **context)
    
    def log_warning(self, message: str, **context):
        """记录警告日志"""
        self.log_aggregator.add_entry("warning", message, **context)
    
    def log_error(self, message: str, **context):
        """记录错误日志"""
        self.log_aggregator.add_entry("error", message, **context)
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取仪表盘数据"""
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": self.metrics.get_metrics(),
            "cost": self.cost_tracker.get_cost_summary(),
            "alerts": [{
                "id": a.id,
                "severity": a.severity.value,
                "title": a.title,
                "message": a.message,
                "timestamp": datetime.fromtimestamp(a.timestamp).isoformat(),
                "metadata": a.metadata
            } for a in self.alert_manager.get_active_alerts()],
            "recent_errors": [{
                "timestamp": datetime.fromtimestamp(e.timestamp).isoformat(),
                "message": e.message,
                "context": e.context
            } for e in self.log_aggregator.get_recent_errors(5)],
            "error_rate": self.log_aggregator.get_error_rate()
        }
    
    def export_prometheus_metrics(self) -> str:
        """导出Prometheus格式指标"""
        return self.prometheus_exporter.generate_metrics_text()
    
    def export_logs(self, filepath: str):
        """导出日志"""
        self.log_aggregator.export_to_file(filepath)
    
    def check_health(self) -> Dict[str, Any]:
        """健康检查"""
        alerts = self.alert_manager.get_active_alerts()
        critical_alerts = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
        
        return {
            "status": "unhealthy" if critical_alerts else "healthy",
            "active_alerts": len(alerts),
            "critical_alerts": len(critical_alerts),
            "timestamp": datetime.now().isoformat()
        }


# ==================== 装饰器 ====================

def observe(operation_name: str):
    """装饰器：自动监控操作"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            observability_center.log_info(f"开始操作: {operation_name}")
            
            try:
                result = await func(*args, **kwargs)
                latency_ms = (time.time() - start_time) * 1000
                observability_center.record_latency(operation_name, latency_ms)
                observability_center.record_request(operation_name)
                observability_center.log_info(f"操作完成: {operation_name}, 耗时: {latency_ms:.2f}ms")
                return result
            except Exception as e:
                observability_center.record_error(operation_name, e)
                raise
            finally:
                observability_center.record_compute_time((time.time() - start_time) * 1000)
        
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            observability_center.log_info(f"开始操作: {operation_name}")
            
            try:
                result = func(*args, **kwargs)
                latency_ms = (time.time() - start_time) * 1000
                observability_center.record_latency(operation_name, latency_ms)
                observability_center.record_request(operation_name)
                observability_center.log_info(f"操作完成: {operation_name}, 耗时: {latency_ms:.2f}ms")
                return result
            except Exception as e:
                observability_center.record_error(operation_name, e)
                raise
            finally:
                observability_center.record_compute_time((time.time() - start_time) * 1000)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


# ==================== 全局实例 ====================

# 延迟导入避免循环依赖
observability_center = None

def init_observability():
    """初始化可观测性中心"""
    global observability_center
    if observability_center is None:
        observability_center = ObservabilityCenter()
    return observability_center


# ==================== 示例用法 ====================

if __name__ == "__main__":
    init_observability()
    
    @observe("test_operation")
    def test_operation(delay_ms: int):
        import time
        time.sleep(delay_ms / 1000)
        return "success"
    
    # 模拟一些操作
    for i in range(10):
        test_operation(100 + i * 50)
    
    # 记录一些Token使用
    observability_center.record_token_usage(100, 50)
    observability_center.record_token_usage(200, 100)
    
    # 打印仪表盘数据
    print("\n=== 仪表盘数据 ===")
    dashboard = observability_center.get_dashboard_data()
    print(json.dumps(dashboard, ensure_ascii=False, indent=2))
    
    # 打印Prometheus指标
    print("\n=== Prometheus指标 ===")
    print(observability_center.export_prometheus_metrics())
    
    # 健康检查
    print("\n=== 健康检查 ===")
    print(json.dumps(observability_center.check_health(), indent=2))