#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
置信度监控与告警模块
提供置信度分布监控和异常告警功能
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AlertRule:
    """告警规则"""

    def __init__(
        self,
        name: str,
        condition: Callable[[Dict[str, Any]], bool],
        severity: str = "warning",
        message_template: str = None
    ):
        self.name = name
        self.condition = condition
        self.severity = severity
        self.message_template = message_template or "{name}: 告警触发"

    def evaluate(self, metrics: Dict[str, Any]) -> Optional[str]:
        """评估规则
        
        Args:
            metrics: 指标数据
            
        Returns:
            告警消息，如果不触发返回None
        """
        try:
            if self.condition(metrics):
                return self.message_template.format(name=self.name, **metrics)
        except Exception as e:
            logger.warning(f"告警规则评估失败 {self.name}: {e}")
        return None


class ConfidenceMonitor:
    """置信度监控器
    
    监控置信度分布漂移、异常值等关键指标
    """

    def __init__(self):
        """初始化置信度监控器"""
        self.confidence_history: List[float] = []
        self.max_history_size = 10000
        
        self.level_counts = defaultdict(int)
        
        self.alert_rules: Dict[str, AlertRule] = {}
        self.alert_history: List[Dict[str, Any]] = []
        self.max_alert_history = 1000
        
        self._setup_default_rules()
        
        logger.info("置信度监控器初始化完成")

    def _setup_default_rules(self):
        """设置默认告警规则"""
        self.add_alert_rule(AlertRule(
            name="high_confidence_drift",
            condition=lambda m: m.get("avg_confidence", 0.5) > 0.9 and m.get("drift_detected", False),
            severity="warning",
            message_template="检测到置信度漂移: 平均置信度 {avg_confidence:.2f} 异常偏高"
        ))
        
        self.add_alert_rule(AlertRule(
            name="low_confidence_drift",
            condition=lambda m: m.get("avg_confidence", 0.5) < 0.3 and m.get("drift_detected", False),
            severity="critical",
            message_template="检测到严重置信度下降: 平均置信度 {avg_confidence:.2f}"
        ))
        
        self.add_alert_rule(AlertRule(
            name="high_error_rate",
            condition=lambda m: m.get("error_rate", 0) > 0.1,
            severity="critical",
            message_template="错误率过高: {error_rate:.2%}"
        ))
        
        self.add_alert_rule(AlertRule(
            name="very_low_confidence_spike",
            condition=lambda m: m.get("very_low_ratio", 0) > 0.5,
            severity="warning",
            message_template="极低置信度比例异常: {very_low_ratio:.2%}"
        ))
        
        self.add_alert_rule(AlertRule(
            name="confidence_variance_high",
            condition=lambda m: m.get("variance", 0) > 0.1,
            severity="info",
            message_template="置信度方差异常: {variance:.4f}"
        ))

    def add_alert_rule(self, rule: AlertRule):
        """添加告警规则
        
        Args:
            rule: 告警规则
        """
        self.alert_rules[rule.name] = rule
        logger.info(f"添加告警规则: {rule.name}")

    def remove_alert_rule(self, rule_name: str) -> bool:
        """移除告警规则
        
        Args:
            rule_name: 规则名称
            
        Returns:
            是否成功移除
        """
        if rule_name in self.alert_rules:
            del self.alert_rules[rule_name]
            logger.info(f"移除告警规则: {rule_name}")
            return True
        return False

    def record_confidence(self, confidence_score: float, level: str = None):
        """记录置信度
        
        Args:
            confidence_score: 置信度分数
            confidence_level: 置信度级别
        """
        self.confidence_history.append(confidence_score)
        
        if len(self.confidence_history) > self.max_history_size:
            self.confidence_history = self.confidence_history[-self.max_history_size:]
        
        if level:
            self.level_counts[level] += 1

    def get_current_metrics(self) -> Dict[str, Any]:
        """获取当前指标
        
        Returns:
            当前指标数据
        """
        if not self.confidence_history:
            return {
                "avg_confidence": 0.0,
                "median_confidence": 0.0,
                "variance": 0.0,
                "std_dev": 0.0,
                "min_confidence": 0.0,
                "max_confidence": 0.0,
                "total_samples": 0,
                "drift_detected": False
            }
        
        history = self.confidence_history[-100:]
        
        avg = statistics.mean(history)
        median = statistics.median(history)
        variance = statistics.variance(history) if len(history) > 1 else 0.0
        std_dev = statistics.stdev(history) if len(history) > 1 else 0.0
        
        old_avg = None
        if len(self.confidence_history) >= 200:
            old_avg = statistics.mean(self.confidence_history[-200:-100])
        
        drift_detected = False
        if old_avg is not None and abs(avg - old_avg) > 0.15:
            drift_detected = True
        
        very_low_count = sum(1 for c in history if c < 0.2)
        very_low_ratio = very_low_count / len(history) if history else 0
        
        high_count = sum(1 for c in history if c >= 0.8)
        high_ratio = high_count / len(history) if history else 0
        
        low_count = sum(1 for c in history if c < 0.4)
        low_ratio = low_count / len(history) if history else 0
        
        return {
            "avg_confidence": round(avg, 4),
            "median_confidence": round(median, 4),
            "variance": round(variance, 6),
            "std_dev": round(std_dev, 4),
            "min_confidence": round(min(history), 4),
            "max_confidence": round(max(history), 4),
            "total_samples": len(self.confidence_history),
            "recent_samples": len(history),
            "drift_detected": drift_detected,
            "very_low_ratio": round(very_low_ratio, 4),
            "high_ratio": round(high_ratio, 4),
            "low_ratio": round(low_ratio, 4),
            "level_counts": dict(self.level_counts)
        }

    def check_alerts(self) -> List[Dict[str, Any]]:
        """检查告警
        
        Returns:
            触发的告警列表
        """
        metrics = self.get_current_metrics()
        triggered_alerts = []
        
        for rule_name, rule in self.alert_rules.items():
            message = rule.evaluate(metrics)
            
            if message:
                alert = {
                    "rule_name": rule_name,
                    "severity": rule.severity,
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                    "metrics": {k: v for k, v in metrics.items() if not isinstance(v, dict)}
                }
                
                triggered_alerts.append(alert)
                
                self.alert_history.append(alert)
                if len(self.alert_history) > self.max_alert_history:
                    self.alert_history = self.alert_history[-self.max_alert_history:]
                
                logger.warning(f"告警触发 [{rule.severity}]: {message}")
        
        return triggered_alerts

    def get_alert_history(self, limit: int = 100, severity: str = None) -> List[Dict[str, Any]]:
        """获取告警历史
        
        Args:
            limit: 限制数量
            severity: 按严重性过滤
            
        Returns:
            告警历史列表
        """
        alerts = self.alert_history
        
        if severity:
            alerts = [a for a in alerts if a["severity"] == severity]
        
        return alerts[-limit:]

    def get_drift_status(self) -> Dict[str, Any]:
        """获取漂移状态
        
        Returns:
            漂移状态信息
        """
        if len(self.confidence_history) < 200:
            return {
                "drift_detected": False,
                "message": "样本不足，无法检测漂移"
            }
        
        recent = self.confidence_history[-100:]
        older = self.confidence_history[-200:-100]
        
        recent_avg = statistics.mean(recent)
        older_avg = statistics.mean(older)
        
        drift_magnitude = abs(recent_avg - older_avg)
        
        if drift_magnitude > 0.15:
            status = "significant_drift"
            message = f"检测到显著漂移: {older_avg:.3f} -> {recent_avg:.3f}"
        elif drift_magnitude > 0.08:
            status = "minor_drift"
            message = f"检测到轻微漂移: {older_avg:.3f} -> {recent_avg:.3f}"
        else:
            status = "stable"
            message = f"置信度分布稳定: {recent_avg:.3f}"
        
        return {
            "status": status,
            "message": message,
            "drift_detected": status != "stable",
            "recent_avg": round(recent_avg, 4),
            "older_avg": round(older_avg, 4),
            "drift_magnitude": round(drift_magnitude, 4)
        }

    def reset_statistics(self):
        """重置统计信息"""
        self.confidence_history.clear()
        self.level_counts.clear()
        self.alert_history.clear()
        logger.info("置信度监控统计已重置")


class ConfidenceAlertManager:
    """置信度告警管理器
    
    管理告警规则、通知和历史
    """

    def __init__(self):
        """初始化置信度告警管理器"""
        self.monitor = ConfidenceMonitor()
        self.notification_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        
        logger.info("置信度告警管理器初始化完成")

    def add_notification_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """添加通知回调
        
        Args:
            callback: 通知回调函数
        """
        self.notification_callbacks.append(callback)

    def remove_notification_callback(self, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """移除通知回调
        
        Args:
            callback: 通知回调函数
            
        Returns:
            是否成功移除
        """
        if callback in self.notification_callbacks:
            self.notification_callbacks.remove(callback)
            return True
        return False

    def process_confidence_result(self, confidence_score: float, confidence_level: str = None, metadata: Dict[str, Any] = None):
        """处理置信度结果
        
        Args:
            confidence_score: 置信度分数
            confidence_level: 置信度级别
            metadata: 元数据
        """
        self.monitor.record_confidence(confidence_score, confidence_level)
        
        triggered_alerts = self.monitor.check_alerts()
        
        for alert in triggered_alerts:
            if metadata:
                alert["metadata"] = metadata
            
            for callback in self.notification_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(f"通知回调执行失败: {e}")

    def get_system_health(self) -> Dict[str, Any]:
        """获取系统健康状态
        
        Returns:
            系统健康状态
        """
        metrics = self.monitor.get_current_metrics()
        drift_status = self.monitor.get_drift_status()
        
        health_score = 1.0
        
        if drift_status["drift_detected"]:
            health_score *= 0.8
        
        if metrics.get("error_rate", 0) > 0.1:
            health_score *= 0.7
        
        if metrics.get("very_low_ratio", 0) > 0.5:
            health_score *= 0.6
        
        if health_score >= 0.8:
            health_status = "healthy"
        elif health_score >= 0.6:
            health_status = "degraded"
        else:
            health_status = "unhealthy"
        
        return {
            "health_status": health_status,
            "health_score": round(health_score, 3),
            "metrics": metrics,
            "drift_status": drift_status,
            "alert_count": len(self.monitor.alert_history),
            "timestamp": datetime.now().isoformat()
        }

    def get_monitoring_summary(self) -> Dict[str, Any]:
        """获取监控摘要
        
        Returns:
            监控摘要
        """
        return {
            "monitor": {
                "total_samples": len(self.monitor.confidence_history),
                "level_counts": dict(self.monitor.level_counts)
            },
            "alerts": {
                "active_rules": len(self.monitor.alert_rules),
                "total_triggered": len(self.monitor.alert_history),
                "recent_critical": len(self.monitor.get_alert_history(severity="critical")),
                "recent_warning": len(self.monitor.get_alert_history(severity="warning"))
            },
            "health": self.get_system_health()
        }


# 全局告警管理器实例
confidence_alert_manager = ConfidenceAlertManager()