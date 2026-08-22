#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLO/SLA 定义与告警规则引擎
实现服务级别目标管理和智能告警系统
"""

import logging
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SLOSeverity(Enum):
    """SLO 严重级别"""
    CRITICAL = "critical"    # 需要立即响应 (< 15分钟)
    WARNING = "warning"      # 需要关注 (< 1小时)
    INFO = "info"            # 信息性通知


class SLOStatus(Enum):
    """SLO 状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BREACHED = "breached"


@dataclass
class SLO:
    """服务级别目标定义"""
    name: str
    description: str
    metric: str
    target: float          # 目标值（如 0.999 表示 99.9%）
    warning_threshold: float  # 警告阈值（如 0.99 表示 99%）
    window: timedelta      # 评估窗口（如 5分钟）
    severity: SLOSeverity
    owner: str             # 负责人
    tags: List[str] = field(default_factory=list)
    
    def check_status(self, current_value: float) -> SLOStatus:
        """检查 SLO 状态"""
        if current_value >= self.target:
            return SLOStatus.HEALTHY
        elif current_value >= self.warning_threshold:
            return SLOStatus.DEGRADED
        else:
            return SLOStatus.BREACHED


@dataclass
class Alert:
    """告警对象"""
    id: str
    slo_name: str
    severity: SLOSeverity
    status: SLOStatus
    current_value: float
    target: float
    message: str
    timestamp: float
    resolved: bool = False
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[float] = None


class AlertRule:
    """告警规则"""
    
    def __init__(
        self,
        name: str,
        slo: SLO,
        condition: Callable[[float], bool],
        notification_channels: List[str],
        auto_remediation: Optional[Callable] = None
    ):
        self.name = name
        self.slo = slo
        self.condition = condition
        self.notification_channels = notification_channels
        self.auto_remediation = auto_remediation
        self.last_triggered = 0
        self.cooldown_period = 300  # 5分钟冷却期
    
    def should_trigger(self, current_value: float) -> bool:
        """检查是否应该触发告警"""
        if time.time() - self.last_triggered < self.cooldown_period:
            return False
        return self.condition(current_value)
    
    def trigger(self, current_value: float) -> Alert:
        """触发告警"""
        self.last_triggered = time.time()
        
        status = self.slo.check_status(current_value)
        alert = Alert(
            id=f"{self.name}-{int(time.time())}",
            slo_name=self.slo.name,
            severity=self.slo.severity,
            status=status,
            current_value=current_value,
            target=self.slo.target,
            message=f"SLO {self.slo.name} 状态: {status.value}, 当前值: {current_value:.4f}, 目标: {self.slo.target}",
            timestamp=time.time()
        )
        
        # 自动修复
        if self.auto_remediation and status == SLOStatus.BREACHED:
            try:
                self.auto_remediation()
                logger.info(f"自动修复执行成功: {self.name}")
            except Exception as e:
                logger.error(f"自动修复失败: {e}")
        
        return alert


class NotificationChannel:
    """通知渠道基类"""
    
    def __init__(self, name: str):
        self.name = name
    
    def send(self, alert: Alert):
        """发送通知"""
        pass


class PagerDutyChannel(NotificationChannel):
    """PagerDuty 通知渠道"""
    
    def __init__(self, api_key: str, service_id: str):
        super().__init__("pagerduty")
        self.api_key = api_key
        self.service_id = service_id
    
    def send(self, alert: Alert):
        """发送到 PagerDuty"""
        logger.info(f"📞 发送 PagerDuty 告警: [{alert.severity.value}] {alert.message}")


class SlackChannel(NotificationChannel):
    """Slack 通知渠道"""
    
    def __init__(self, webhook_url: str, channel: str):
        super().__init__("slack")
        self.webhook_url = webhook_url
        self.channel = channel
    
    def send(self, alert: Alert):
        """发送到 Slack"""
        logger.info(f"📱 发送 Slack 通知到 #{self.channel}: [{alert.severity.value}] {alert.message}")


class EmailChannel(NotificationChannel):
    """Email 通知渠道"""
    
    def __init__(self, smtp_server: str, smtp_port: int, from_email: str, to_emails: List[str]):
        super().__init__("email")
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.from_email = from_email
        self.to_emails = to_emails
    
    def send(self, alert: Alert):
        """发送邮件"""
        logger.info(f"📧 发送邮件告警到 {self.to_emails}: [{alert.severity.value}] {alert.message}")


class AlertManager:
    """告警管理器"""
    
    def __init__(self):
        self.rules: List[AlertRule] = []
        self.channels: Dict[str, NotificationChannel] = {}
        self.active_alerts: List[Alert] = []
        self.alert_history: List[Alert] = []
    
    def add_rule(self, rule: AlertRule):
        """添加告警规则"""
        self.rules.append(rule)
        logger.info(f"添加告警规则: {rule.name}")
    
    def add_channel(self, channel: NotificationChannel):
        """添加通知渠道"""
        self.channels[channel.name] = channel
    
    def evaluate_rules(self, metrics: Dict[str, float]):
        """评估所有规则"""
        new_alerts = []
        
        for rule in self.rules:
            if rule.slo.metric in metrics:
                current_value = metrics[rule.slo.metric]
                
                if rule.should_trigger(current_value):
                    alert = rule.trigger(current_value)
                    new_alerts.append(alert)
                    self.active_alerts.append(alert)
                    self.alert_history.append(alert)
                    
                    # 发送通知
                    self._notify(alert, rule.notification_channels)
        
        return new_alerts
    
    def _notify(self, alert: Alert, channels: List[str]):
        """发送通知到指定渠道"""
        for channel_name in channels:
            if channel_name in self.channels:
                try:
                    self.channels[channel_name].send(alert)
                except Exception as e:
                    logger.error(f"通知发送失败 ({channel_name}): {e}")
    
    def acknowledge_alert(self, alert_id: str, user: str):
        """确认告警"""
        for alert in self.active_alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_by = user
                logger.info(f"告警已确认: {alert_id} by {user}")
                return True
        return False
    
    def resolve_alert(self, alert_id: str):
        """解决告警"""
        for alert in self.active_alerts:
            if alert.id == alert_id:
                alert.resolved = True
                alert.resolved_at = time.time()
                self.active_alerts.remove(alert)
                logger.info(f"告警已解决: {alert_id}")
                return True
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活动告警"""
        return self.active_alerts
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """获取告警历史"""
        return self.alert_history[-limit:]


# ==================== 预定义的 SLO 模板 ====================

def create_default_slos() -> List[SLO]:
    """创建默认的 SLO 定义"""
    return [
        # API 可用性 SLO
        SLO(
            name="API_Availability",
            description="API 调用成功率",
            metric="api_availability",
            target=0.999,
            warning_threshold=0.99,
            window=timedelta(minutes=5),
            severity=SLOSeverity.CRITICAL,
            owner="backend-team",
            tags=["api", "availability"]
        ),
        # 延迟 SLO
        SLO(
            name="API_Latency_P95",
            description="API 95th 百分位延迟",
            metric="api_latency_p95",
            target=0.3,  # 300ms
            warning_threshold=0.5,  # 500ms
            window=timedelta(minutes=5),
            severity=SLOSeverity.WARNING,
            owner="backend-team",
            tags=["api", "latency"]
        ),
        # 错误率 SLO
        SLO(
            name="API_Error_Rate",
            description="API 错误率",
            metric="api_error_rate",
            target=0.001,  # 0.1%
            warning_threshold=0.01,  # 1%
            window=timedelta(minutes=5),
            severity=SLOSeverity.CRITICAL,
            owner="backend-team",
            tags=["api", "errors"]
        ),
        # CPU 利用率 SLO
        SLO(
            name="CPU_Utilization",
            description="CPU 利用率",
            metric="cpu_utilization",
            target=0.7,  # 70%
            warning_threshold=0.85,  # 85%
            window=timedelta(minutes=10),
            severity=SLOSeverity.WARNING,
            owner="devops-team",
            tags=["infrastructure", "cpu"]
        ),
        # 内存利用率 SLO
        SLO(
            name="Memory_Utilization",
            description="内存利用率",
            metric="memory_utilization",
            target=0.7,  # 70%
            warning_threshold=0.85,  # 85%
            window=timedelta(minutes=10),
            severity=SLOSeverity.WARNING,
            owner="devops-team",
            tags=["infrastructure", "memory"]
        ),
        # Token 消耗 SLO
        SLO(
            name="Token_Cost",
            description="Token 消耗成本",
            metric="token_cost_usd",
            target=10.0,  # $10/hour
            warning_threshold=5.0,  # $5/hour
            window=timedelta(hours=1),
            severity=SLOSeverity.WARNING,
            owner="finance-team",
            tags=["cost", "tokens"]
        )
    ]


def create_default_alerts(alert_manager: AlertManager):
    """创建默认告警规则"""
    slos = create_default_slos()
    
    # 定义自动修复函数
    def scale_up_remediation():
        """扩容修复"""
        logger.info("🔄 执行自动扩容...")
    
    def restart_service_remediation():
        """重启服务修复"""
        logger.info("🔄 执行服务重启...")
    
    def cleanup_cache_remediation():
        """清理缓存修复"""
        logger.info("🔄 执行缓存清理...")
    
    # 创建告警规则
    for slo in slos:
        rule_name = f"alert_{slo.name}"
        
        # 定义触发条件
        def condition_factory(slo_ref):
            def condition(current_value):
                status = slo_ref.check_status(current_value)
                return status in [SLOStatus.DEGRADED, SLOStatus.BREACHED]
            return condition
        
        # 选择通知渠道
        channels = ["slack"]
        if slo.severity == SLOSeverity.CRITICAL:
            channels.append("pagerduty")
        
        # 选择自动修复
        auto_remediation = None
        if slo.name in ["API_Availability", "API_Error_Rate"]:
            auto_remediation = restart_service_remediation
        elif slo.name in ["CPU_Utilization", "Memory_Utilization"]:
            auto_remediation = scale_up_remediation
        
        rule = AlertRule(
            name=rule_name,
            slo=slo,
            condition=condition_factory(slo),
            notification_channels=channels,
            auto_remediation=auto_remediation
        )
        
        alert_manager.add_rule(rule)


# ==================== 全局实例 ====================

alert_manager = AlertManager()


def init_alerting():
    """初始化告警系统"""
    # 添加通知渠道
    alert_manager.add_channel(SlackChannel(
        webhook_url="https://hooks.slack.com/services/XXX",
        channel="ops-alerts"
    ))
    
    alert_manager.add_channel(PagerDutyChannel(
        api_key="your-api-key",
        service_id="your-service-id"
    ))
    
    # 创建默认告警规则
    create_default_alerts(alert_manager)
    
    logger.info("告警系统初始化完成")
    return alert_manager


# ==================== 示例用法 ====================

if __name__ == "__main__":
    # 初始化告警系统
    manager = init_alerting()
    
    # 模拟指标数据
    metrics = {
        "api_availability": 0.95,  # 低于目标 0.999
        "api_latency_p95": 0.25,    # 正常
        "api_error_rate": 0.02,     # 高于目标 0.001
        "cpu_utilization": 0.88,    # 高于警告阈值
        "memory_utilization": 0.65, # 正常
        "token_cost_usd": 3.5       # 正常
    }
    
    # 评估规则
    print("评估告警规则...")
    new_alerts = manager.evaluate_rules(metrics)
    
    print(f"\n触发的告警数量: {len(new_alerts)}")
    for alert in new_alerts:
        print(f"  - [{alert.severity.value}] {alert.slo_name}: {alert.message}")
    
    # 确认告警
    if new_alerts:
        print("\n确认告警...")
        manager.acknowledge_alert(new_alerts[0].id, "oncall-user")
    
    # 获取活动告警
    print(f"\n活动告警数量: {len(manager.get_active_alerts())}")
    
    # 解决告警
    if new_alerts:
        print("\n解决告警...")
        manager.resolve_alert(new_alerts[0].id)
    
    print(f"\n活动告警数量: {len(manager.get_active_alerts())}")