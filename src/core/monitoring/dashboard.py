#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控仪表盘
提供系统状态、性能指标和推理过程的可视化接口
"""
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

from .metrics import MetricsCollector, get_metrics_collector

logger = logging.getLogger(__name__)


@dataclass
class DashboardWidget:
    """仪表盘组件"""
    id: str
    title: str
    type: str  # chart, gauge, table, info
    data: Dict[str, Any] = field(default_factory=dict)
    position: Dict[str, int] = field(default_factory=dict)


@dataclass
class SystemStatus:
    """系统状态"""
    status: str  # healthy, warning, error, offline
    uptime: float
    components: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    last_update: str = ""


class MonitoringDashboard:
    """监控仪表盘"""
    
    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        self.metrics = metrics_collector or get_metrics_collector()
        self.widgets: Dict[str, DashboardWidget] = {}
        self.system_status = SystemStatus(
            status="healthy",
            uptime=0.0,
            last_update=datetime.now().isoformat()
        )
        self.start_time = datetime.now()
        self.alerts: List[Dict[str, Any]] = []
    
    def update_system_status(self, component_name: str, status_info: Dict[str, Any]):
        """更新组件状态"""
        self.system_status.components[component_name] = status_info
        self.system_status.last_update = datetime.now().isoformat()
        self.system_status.uptime = (datetime.now() - self.start_time).total_seconds()
        
        # 计算整体状态
        overall_status = "healthy"
        for component, info in self.system_status.components.items():
            if info.get("status") == "error":
                overall_status = "error"
                break
            elif info.get("status") == "warning" and overall_status == "healthy":
                overall_status = "warning"
        
        self.system_status.status = overall_status
        logger.info(f"System status updated: {overall_status}")
    
    def add_widget(self, widget: DashboardWidget):
        """添加仪表盘组件"""
        self.widgets[widget.id] = widget
        logger.debug(f"Widget {widget.id} added to dashboard")
    
    def remove_widget(self, widget_id: str):
        """移除组件"""
        if widget_id in self.widgets:
            del self.widgets[widget_id]
            logger.debug(f"Widget {widget_id} removed")
    
    def create_performance_widget(self) -> DashboardWidget:
        """创建性能统计组件"""
        stats = self.metrics.get_statistics()
        
        widget = DashboardWidget(
            id="performance",
            title="Performance Metrics",
            type="table",
            data={
                "performance": stats.get("performance", {}),
                "counters": stats.get("counters", {})
            },
            position={"x": 0, "y": 0, "w": 12, "h": 4}
        )
        
        self.widgets["performance"] = widget
        return widget
    
    def create_memory_widget(self, memory_system) -> DashboardWidget:
        """创建记忆系统组件"""
        memory_stats = {
            "total_memories": 0,
            "short_term": 0,
            "medium_term": 0,
            "long_term": 0,
            "last_optimization": None
        }
        
        if hasattr(memory_system, 'get_statistics'):
            memory_stats.update(memory_system.get_statistics())
        
        widget = DashboardWidget(
            id="memory",
            title="Memory System",
            type="chart",
            data=memory_stats,
            position={"x": 0, "y": 4, "w": 6, "h": 4}
        )
        
        self.widgets["memory"] = widget
        return widget
    
    def create_reasoning_widget(self, reasoning_history: List[Dict[str, Any]]) -> DashboardWidget:
        """创建推理过程组件"""
        widget = DashboardWidget(
            id="reasoning",
            title="Reasoning History",
            type="table",
            data={
                "recent_reasoning": reasoning_history[-10:],  # 最近10条
                "total_count": len(reasoning_history)
            },
            position={"x": 6, "y": 4, "w": 6, "h": 4}
        )
        
        self.widgets["reasoning"] = widget
        return widget
    
    def add_alert(self, level: str, message: str, metadata: Optional[Dict[str, Any]] = None):
        """添加警报"""
        alert = {
            "level": level,  # info, warning, error, critical
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self.alerts.append(alert)
        logger.warning(f"Alert [{level}]: {message}")
        
        # 更新系统状态
        if level in ["error", "critical"] and self.system_status.status != "error":
            self.system_status.status = "warning" if level == "error" else "error"
    
    def get_alerts(self, level: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取警报"""
        if level:
            return [a for a in self.alerts if a["level"] == level]
        return self.alerts
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取完整仪表盘数据"""
        # 更新性能组件
        self.create_performance_widget()
        
        return {
            "system_status": {
                "status": self.system_status.status,
                "uptime": self.system_status.uptime,
                "components": self.system_status.components,
                "last_update": self.system_status.last_update
            },
            "widgets": [
                {
                    "id": w.id,
                    "title": w.title,
                    "type": w.type,
                    "data": w.data,
                    "position": w.position
                }
                for w in self.widgets.values()
            ],
            "alerts": self.alerts[-20:],  # 最近20条警报
            "metrics": self.metrics.get_statistics(),
            "timestamp": datetime.now().isoformat()
        }
    
    def export_dashboard(self, filepath: str):
        """导出仪表盘数据"""
        data = self.get_dashboard_data()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Dashboard exported to {filepath}")
    
    def reset(self):
        """重置仪表盘"""
        self.widgets.clear()
        self.alerts.clear()
        self.system_status = SystemStatus(
            status="healthy",
            uptime=0.0,
            last_update=datetime.now().isoformat()
        )
        self.start_time = datetime.now()
        logger.info("Dashboard reset")


# 全局仪表盘实例
_global_dashboard = None


def get_dashboard() -> MonitoringDashboard:
    """获取全局仪表盘"""
    global _global_dashboard
    if _global_dashboard is None:
        _global_dashboard = MonitoringDashboard()
    return _global_dashboard
