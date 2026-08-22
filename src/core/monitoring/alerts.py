"""
告警系统 - 提供告警规则和告警管理
"""
import time
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class Alert:
    """告警实例"""
    id: str
    rule_name: str
    severity: AlertSeverity
    message: str
    timestamp: float
    value: Optional[float] = None
    threshold: Optional[float] = None
    resolved: bool = False
    resolved_at: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'rule_name': self.rule_name,
            'severity': self.severity.value,
            'message': self.message,
            'timestamp': self.timestamp,
            'value': self.value,
            'threshold': self.threshold,
            'resolved': self.resolved,
            'resolved_at': self.resolved_at
        }

@dataclass
class AlertRule:
    """告警规则"""
    name: str
    metric_name: str
    condition: str  # "above", "below", "equals"
    threshold: float
    severity: AlertSeverity
    message_template: str
    duration_seconds: int = 0  # 持续多久才触发
    enabled: bool = True
    cooldown_seconds: int = 60  # 告警冷却时间
    
    def check(self, current_value: float) -> bool:
        """检查是否触发告警"""
        if self.condition == "above":
            return current_value > self.threshold
        elif self.condition == "below":
            return current_value < self.threshold
        elif self.condition == "equals":
            return current_value == self.threshold
        return False
        
    def build_message(self, current_value: float) -> str:
        """构建告警消息"""
        return self.message_template.format(
            value=current_value,
            threshold=self.threshold,
            rule_name=self.name
        )

class AlertManager:
    """告警管理器"""
    
    def __init__(self, metrics_collector=None):
        self.rules: List[AlertRule] = []
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self._last_alert_time: Dict[str, float] = {}
        self._callbacks: List[Callable] = []
        self.metrics_collector = metrics_collector
        self._lock = asyncio.Lock()
        self._running = False
        self._check_task = None
        
    def add_rule(self, rule: AlertRule):
        """添加告警规则"""
        self.rules.append(rule)
        logger.info(f"📋 添加告警规则: {rule.name}")
        
    def remove_rule(self, rule_name: str):
        """移除告警规则"""
        self.rules = [r for r in self.rules if r.name != rule_name]
        logger.info(f"🗑️ 移除告警规则: {rule_name}")
        
    def register_callback(self, callback: Callable):
        """注册告警回调"""
        self._callbacks.append(callback)
        
    async def check_rules(self):
        """检查所有告警规则"""
        if not self.metrics_collector:
            return
            
        async with self._lock:
            for rule in self.rules:
                if not rule.enabled:
                    continue
                    
                metric = await self.metrics_collector.get_metric(rule.metric_name)
                if not metric:
                    continue
                    
                latest = metric.get_latest()
                if not latest:
                    continue
                    
                current_value = latest.value
                should_trigger = rule.check(current_value)
                
                if should_trigger:
                    await self._trigger_alert(rule, current_value)
                else:
                    await self._resolve_alert(rule.name)
                    
    async def _trigger_alert(self, rule: AlertRule, current_value: float):
        """触发告警"""
        now = time.time()
        
        last_time = self._last_alert_time.get(rule.name, 0)
        if now - last_time < rule.cooldown_seconds:
            return
            
        alert_id = f"{rule.name}:{int(now)}"
        
        if rule.name in self.active_alerts:
            return
            
        alert = Alert(
            id=alert_id,
            rule_name=rule.name,
            severity=rule.severity,
            message=rule.build_message(current_value),
            timestamp=now,
            value=current_value,
            threshold=rule.threshold
        )
        
        self.active_alerts[rule.name] = alert
        self.alert_history.append(alert)
        self._last_alert_time[rule.name] = now
        
        logger.warning(f"🚨 触发告警: {rule.name} - {alert.message}")
        
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"⚠️ 告警回调执行失败: {e}")
                
    async def _resolve_alert(self, rule_name: str):
        """解决告警"""
        if rule_name not in self.active_alerts:
            return
            
        alert = self.active_alerts[rule_name]
        alert.resolved = True
        alert.resolved_at = time.time()
        
        del self.active_alerts[rule_name]
        
        logger.info(f"✅ 告警已解决: {rule_name}")
        
    async def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        return list(self.active_alerts.values())
        
    async def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """获取告警历史"""
        return self.alert_history[-limit:]
        
    async def start(self, check_interval: int = 10):
        """启动告警检查"""
        if self._running:
            return
            
        self._running = True
        logger.info("🚀 告警管理器已启动")
        
        async def check_loop():
            while self._running:
                try:
                    await self.check_rules()
                except Exception as e:
                    logger.error(f"⚠️ 告警检查失败: {e}")
                await asyncio.sleep(check_interval)
                
        self._check_task = asyncio.create_task(check_loop())
        
    async def stop(self):
        """停止告警检查"""
        self._running = False
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
        logger.info("👋 告警管理器已停止")
        
    def get_default_rules(self) -> List[AlertRule]:
        """获取默认告警规则"""
        return [
            AlertRule(
                name="high_api_latency",
                metric_name="api.requests.duration",
                condition="above",
                threshold=2.0,
                severity=AlertSeverity.WARNING,
                message_template="API 响应时间过高: {value:.2f}s > {threshold}s",
                cooldown_seconds=30
            ),
            AlertRule(
                name="high_error_rate",
                metric_name="api.requests.errors",
                condition="above",
                threshold=10.0,
                severity=AlertSeverity.CRITICAL,
                message_template="错误率过高: {value:.0f} errors",
                cooldown_seconds=60
            ),
            AlertRule(
                name="low_cache_hit_rate",
                metric_name="cache.hit_rate",
                condition="below",
                threshold=50.0,
                severity=AlertSeverity.WARNING,
                message_template="缓存命中率过低: {value:.2f}% < {threshold}%",
                cooldown_seconds=120
            )
        ]
