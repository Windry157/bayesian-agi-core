#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可观测性模块包
包含分布式链路追踪、性能指标监控、API速率限制等功能
"""

from .tracing import tracer, trace_method, HAS_OPENTELEMETRY
from .metrics import metrics_collector, monitor_latency, print_metrics_summary
from .rate_limiter import rate_limiter, rate_limit, setup_default_rate_limits, RateLimitExceededError
from .observability_center import (
    observability_center,
    init_observability,
    observe,
    AlertSeverity,
    AlertManager,
    CostTracker,
    PrometheusExporter,
    LogAggregator
)
from .slo_manager import (
    alert_manager,
    init_alerting,
    SLO,
    SLOStatus,
    SLOSeverity,
    AlertRule,
    create_default_slos
)
from .self_healing import (
    get_engine,
    execute_action,
    execute_playbook,
    EngineFactory,
    DefaultSelfHealingEngine,
    RemediationAction,
    RemediationPlaybook,
    RemediationActionFactory,
    RemediationPlaybookLibrary,
    RemediationStatus,
    RemediationPriority,
    RBACManager,
    PermissionDeniedError
)

__all__ = [
    # 追踪模块
    "tracer",
    "trace_method",
    "HAS_OPENTELEMETRY",
    
    # 指标监控模块
    "metrics_collector",
    "monitor_latency",
    "print_metrics_summary",
    
    # 速率限制模块
    "rate_limiter",
    "rate_limit",
    "setup_default_rate_limits",
    "RateLimitExceededError",
    
    # 可观测性中心
    "observability_center",
    "init_observability",
    "observe",
    "AlertSeverity",
    "AlertManager",
    "CostTracker",
    "PrometheusExporter",
    "LogAggregator",
    
    # SLO/SLA 告警系统
    "alert_manager",
    "init_alerting",
    "SLO",
    "SLOStatus",
    "SLOSeverity",
    "AlertRule",
    "create_default_slos",
    
    # 自愈能力系统
    "get_engine",
    "execute_action",
    "execute_playbook",
    "EngineFactory",
    "DefaultSelfHealingEngine",
    "RemediationAction",
    "RemediationPlaybook",
    "RemediationActionFactory",
    "RemediationPlaybookLibrary",
    "RemediationStatus",
    "RemediationPriority",
    "RBACManager",
    "PermissionDeniedError",
]
