#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可观测性模块测试套件
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.observability.observability_center import (
    init_observability,
    observe,
    AlertSeverity,
    CostTracker,
    AlertManager,
    PrometheusExporter,
    LogAggregator
)


class TestCostTracker:
    """成本追踪器测试"""

    def test_record_token_usage(self):
        """测试记录Token使用"""
        tracker = CostTracker()
        
        tracker.record_token_usage(100, 50)
        tracker.record_token_usage(200, 100)
        
        summary = tracker.get_cost_summary()
        
        assert summary["total_input_tokens"] == 300
        assert summary["total_output_tokens"] == 150
        assert summary["total_tokens"] == 450
        assert summary["token_cost_usd"] > 0

    def test_record_compute_time(self):
        """测试记录计算时长"""
        tracker = CostTracker()
        
        tracker.record_compute_time(100)
        tracker.record_compute_time(200)
        
        summary = tracker.get_cost_summary()
        
        assert summary["total_compute_ms"] == 300
        assert summary["compute_cost_usd"] > 0

    def test_cost_summary_empty(self):
        """测试空摘要"""
        tracker = CostTracker()
        summary = tracker.get_cost_summary()
        
        assert summary["total_tokens"] == 0
        assert summary["total_cost_usd"] == 0.0


class TestAlertManager:
    """告警管理器测试"""

    def test_trigger_alert(self):
        """测试触发告警"""
        manager = AlertManager()
        
        manager.trigger_alert("high_latency", "测试告警消息", test_key="test_value")
        
        alerts = manager.get_active_alerts()
        assert len(alerts) == 1
        assert alerts[0].title == "高延迟告警"
        assert alerts[0].severity == AlertSeverity.CRITICAL

    def test_resolve_alert(self):
        """测试解决告警"""
        manager = AlertManager()
        
        manager.trigger_alert("high_latency", "测试告警")
        alert_id = manager.get_active_alerts()[0].id
        
        result = manager.resolve_alert(alert_id)
        assert result is True
        
        active_alerts = manager.get_active_alerts()
        assert len(active_alerts) == 0

    def test_get_alerts_by_severity(self):
        """测试按级别获取告警"""
        manager = AlertManager()
        
        manager.trigger_alert("high_latency", "critical alert")
        manager.trigger_alert("high_error_rate", "warning alert")
        
        critical_alerts = manager.get_alerts_by_severity(AlertSeverity.CRITICAL)
        warning_alerts = manager.get_alerts_by_severity(AlertSeverity.WARNING)
        
        assert len(critical_alerts) == 1
        assert len(warning_alerts) == 1


class TestPrometheusExporter:
    """Prometheus导出器测试"""

    def test_add_counter(self):
        """测试添加计数器"""
        exporter = PrometheusExporter()
        
        exporter.add_counter("test_counter", 1)
        exporter.add_counter("test_counter", 2)
        
        metrics_text = exporter.generate_metrics_text()
        assert "test_counter" in metrics_text
        assert "3" in metrics_text  # 1 + 2 = 3

    def test_add_gauge(self):
        """测试添加仪表盘"""
        exporter = PrometheusExporter()
        
        exporter.add_gauge("test_gauge", 42.5)
        
        metrics_text = exporter.generate_metrics_text()
        assert "test_gauge" in metrics_text
        assert "42.5" in metrics_text

    def test_add_histogram(self):
        """测试添加直方图"""
        exporter = PrometheusExporter()
        
        exporter.add_histogram("test_histogram", 1.0)
        exporter.add_histogram("test_histogram", 2.0)
        
        metrics_text = exporter.generate_metrics_text()
        assert "test_histogram_count" in metrics_text
        assert "test_histogram_sum" in metrics_text


class TestLogAggregator:
    """日志聚合器测试"""

    def test_add_entry(self):
        """测试添加日志条目"""
        aggregator = LogAggregator()
        
        aggregator.add_entry("info", "test message", key="value")
        
        entries = aggregator.get_recent_entries()
        assert len(entries) == 1
        assert entries[0].message == "test message"
        assert entries[0].context["key"] == "value"

    def test_get_recent_errors(self):
        """测试获取最近错误"""
        aggregator = LogAggregator()
        
        aggregator.add_entry("error", "error 1")
        aggregator.add_entry("info", "info 1")
        aggregator.add_entry("error", "error 2")
        
        errors = aggregator.get_recent_errors()
        assert len(errors) == 2
        assert errors[0].message == "error 1"
        assert errors[1].message == "error 2"

    def test_get_error_rate(self):
        """测试获取错误率"""
        aggregator = LogAggregator()
        
        aggregator.add_entry("error", "error")
        aggregator.add_entry("info", "info")
        aggregator.add_entry("info", "info")
        
        error_rate = aggregator.get_error_rate()
        assert error_rate == 1/3  # 1 error out of 3 entries


class TestObservabilityCenter:
    """可观测性中心测试"""

    def test_init_observability(self):
        """测试初始化可观测性中心"""
        center = init_observability()
        
        assert center is not None
        assert center.metrics is not None
        assert center.cost_tracker is not None
        assert center.alert_manager is not None
        assert center.prometheus_exporter is not None
        assert center.log_aggregator is not None

    def test_record_token_usage(self):
        """测试记录Token使用"""
        center = init_observability()
        
        center.record_token_usage(100, 50)
        
        cost = center.cost_tracker.get_cost_summary()
        assert cost["total_input_tokens"] == 100
        assert cost["total_output_tokens"] == 50

    def test_record_latency(self):
        """测试记录延迟"""
        center = init_observability()
        
        center.record_latency("test_operation", 100)
        
        metrics = center.metrics.get_metrics()
        assert "latency_test_operation" in metrics

    def test_observe_decorator(self):
        """测试observe装饰器"""
        center = init_observability()
        
        @observe("decorated_operation")
        def test_func():
            return "done"
        
        result = test_func()
        assert result == "done"
        
        metrics = center.metrics.get_metrics()
        assert "latency_decorated_operation" in metrics

    def test_get_dashboard_data(self):
        """测试获取仪表盘数据"""
        center = init_observability()
        
        dashboard = center.get_dashboard_data()
        
        assert "timestamp" in dashboard
        assert "metrics" in dashboard
        assert "cost" in dashboard
        assert "alerts" in dashboard
        assert "error_rate" in dashboard

    def test_check_health(self):
        """测试健康检查"""
        center = init_observability()
        
        health = center.check_health()
        
        assert "status" in health
        assert "active_alerts" in health
        assert "critical_alerts" in health
        assert health["status"] == "healthy"


def run_observability_tests():
    """运行所有可观测性测试"""
    print("=" * 60)
    print("可观测性模块测试")
    print("=" * 60)

    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
    ])

    return exit_code == 0


if __name__ == "__main__":
    success = run_observability_tests()

    print("\n" + "=" * 60)
    if success:
        print("✅ 所有可观测性测试通过！")
    else:
        print("❌ 部分测试失败")
    print("=" * 60)

    sys.exit(0 if success else 1)
