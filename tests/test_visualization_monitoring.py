#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import pytest
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.visualization.reasoning_visualizer import (
    ReasoningVisualizer,
    VisualizationData,
    VisualizationNode,
    VisualizationEdge,
    VisualizationType,
)

from src.core.monitoring.metrics import (
    MetricsCollector,
    get_metrics_collector,
)

from src.core.monitoring.dashboard import (
    MonitoringDashboard,
    get_dashboard,
)


class TestReasoningVisualizer:
    def test_create_visualizer(self):
        viz = ReasoningVisualizer()
        assert viz is not None
        assert len(viz.history) == 0

    def test_visualize_tree(self):
        viz = ReasoningVisualizer()
        tree_data = {
            "tree_structure": {
                "id": "root",
                "content": "Test problem",
                "type": "initial",
                "value": 0.5,
                "confidence": 0.8,
                "children": [
                    {
                        "id": "child1",
                        "content": "First idea",
                        "type": "idea",
                        "value": 0.7,
                        "confidence": 0.6,
                        "children": [],
                    }
                ],
            }
        }
        viz_data = viz.visualize_tree_of_thought(tree_data)
        assert viz_data.type == VisualizationType.TREE
        assert len(viz_data.nodes) == 2
        assert len(viz_data.edges) == 1
        assert len(viz.history) == 1

    def test_to_json(self):
        viz = ReasoningVisualizer()
        viz_data = VisualizationData(
            type=VisualizationType.TREE,
            nodes=[
                VisualizationNode(id="1", label="Test", type="default", value=0.5),
            ],
            edges=[
                VisualizationEdge(source="1", target="2", type="default"),
            ],
        )
        json_str = viz.to_json(viz_data)
        assert isinstance(json_str, str)
        assert '"nodes"' in json_str


class TestMetricsCollector:
    def test_create_collector(self):
        collector = MetricsCollector()
        assert collector is not None
        assert len(collector.counters) == 0

    def test_increment_counter(self):
        collector = MetricsCollector()
        collector.increment_counter("test_counter")
        assert collector.counters["test_counter"] == 1
        collector.increment_counter("test_counter", value=5)
        assert collector.counters["test_counter"] == 6

    def test_set_gauge(self):
        collector = MetricsCollector()
        collector.set_gauge("test_gauge", 42.5)
        assert collector.gauges["test_gauge"] == 42.5

    def test_measure_performance(self):
        collector = MetricsCollector()

        @collector.measure_performance("test_operation")
        def test_func():
            time.sleep(0.01)
            return "result"

        result = test_func()
        assert result == "result"
        stats = collector.get_statistics()
        assert "test_operation" in stats["performance"]
        assert stats["performance"]["test_operation"]["count"] == 1

    def test_get_statistics(self):
        collector = MetricsCollector()
        collector.increment_counter("requests")
        collector.set_gauge("temperature", 25.5)
        stats = collector.get_statistics()
        assert "counters" in stats
        assert "gauges" in stats
        assert stats["counters"]["requests"] == 1


class TestMonitoringDashboard:
    def test_create_dashboard(self):
        dashboard = MonitoringDashboard()
        assert dashboard is not None
        assert dashboard.system_status.status == "healthy"

    def test_update_system_status(self):
        dashboard = MonitoringDashboard()
        dashboard.update_system_status("memory_system", {
            "status": "healthy",
            "memory_used": 100,
        })
        assert "memory_system" in dashboard.system_status.components
        assert dashboard.system_status.status == "healthy"

    def test_add_alert(self):
        dashboard = MonitoringDashboard()
        dashboard.add_alert("warning", "Low memory warning")
        alerts = dashboard.get_alerts()
        assert len(alerts) == 1
        assert alerts[0]["level"] == "warning"

    def test_create_performance_widget(self):
        dashboard = MonitoringDashboard()
        widget = dashboard.create_performance_widget()
        assert widget is not None
        assert widget.id == "performance"
        assert "performance" in dashboard.widgets

    def test_get_dashboard_data(self):
        dashboard = MonitoringDashboard()
        data = dashboard.get_dashboard_data()
        assert "system_status" in data
        assert "widgets" in data
        assert "alerts" in data
        assert "metrics" in data


class TestGlobalInstances:
    def test_global_collector(self):
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()
        assert collector1 is collector2

    def test_global_dashboard(self):
        dashboard1 = get_dashboard()
        dashboard2 = get_dashboard()
        assert dashboard1 is dashboard2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
