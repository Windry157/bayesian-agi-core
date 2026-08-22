#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
健壮性系统配置加载器
Resilience System Configuration Loader
"""

import yaml
import os
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    enabled: bool = True
    failure_threshold: int = 3
    recovery_timeout: float = 30.0
    expected_exceptions: list = field(default_factory=lambda: ["Exception"])


@dataclass
class RateLimiterConfig:
    """限流器配置"""
    enabled: bool = True
    type: str = "sliding_window"
    requests: int = 100
    period_seconds: float = 60.0
    burst_size: Optional[int] = None


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    json_format: bool = True
    log_dir: str = "logs"
    max_file_size: int = 104857600
    backup_count: int = 10
    daily_rotation: bool = True


@dataclass
class AlertsConfig:
    """告警配置"""
    enabled: bool = True
    circuit_breakers: Dict = field(default_factory=lambda: {
        "max_open": 1,
        "error_rate_threshold": 0.05
    })
    rate_limiting: Dict = field(default_factory=lambda: {
        "reject_rate_threshold": 0.20
    })


@dataclass
class HealthConfig:
    """健康检查配置"""
    enabled: bool = True
    check_interval_seconds: int = 30
    circuit_breaker_check: bool = True
    rate_limiter_check: bool = True
    model_availability_check: bool = True


@dataclass
class ResilienceConfig:
    """完整健壮性配置"""
    circuit_breakers: Dict[str, CircuitBreakerConfig] = field(default_factory=dict)
    rate_limiters: Dict[str, RateLimiterConfig] = field(default_factory=dict)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    alerts: AlertsConfig = field(default_factory=AlertsConfig)
    health: HealthConfig = field(default_factory=HealthConfig)


class ResilienceConfigManager:
    """健壮性配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config.yaml"
        
        self.config_path = Path(config_path)
        self.config: Optional[ResilienceConfig] = None
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        if not self.config_path.exists():
            print(f"Warning: Config file {self.config_path} not found, using defaults")
            self.config = ResilienceConfig()
            return
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        resilience_data = data.get("resilience", {})
        
        # 解析熔断器配置
        circuit_breakers = {}
        for name, cb_data in resilience_data.get("circuit_breakers", {}).items():
            circuit_breakers[name] = CircuitBreakerConfig(
                enabled=cb_data.get("enabled", True),
                failure_threshold=cb_data.get("failure_threshold", 3),
                recovery_timeout=cb_data.get("recovery_timeout", 30.0),
                expected_exceptions=cb_data.get("expected_exceptions", ["Exception"])
            )
        
        # 解析限流器配置
        rate_limiters = {}
        for name, rl_data in resilience_data.get("rate_limiters", {}).items():
            rate_limiters[name] = RateLimiterConfig(
                enabled=rl_data.get("enabled", True),
                type=rl_data.get("type", "sliding_window"),
                requests=rl_data.get("requests", 100),
                period_seconds=rl_data.get("period_seconds", 60.0),
                burst_size=rl_data.get("burst_size", None)
            )
        
        # 解析日志配置
        logging_data = resilience_data.get("logging", {})
        logging_config = LoggingConfig(
            level=logging_data.get("level", "INFO"),
            json_format=logging_data.get("json_format", True),
            log_dir=logging_data.get("log_dir", "logs"),
            max_file_size=logging_data.get("max_file_size", 104857600),
            backup_count=logging_data.get("backup_count", 10),
            daily_rotation=logging_data.get("daily_rotation", True)
        )
        
        # 解析告警配置
        alerts_data = resilience_data.get("alerts", {})
        alerts_config = AlertsConfig(
            enabled=alerts_data.get("enabled", True),
            circuit_breakers=alerts_data.get("circuit_breakers", {
                "max_open": 1,
                "error_rate_threshold": 0.05
            }),
            rate_limiting=alerts_data.get("rate_limiting", {
                "reject_rate_threshold": 0.20
            })
        )
        
        # 解析健康检查配置
        health_data = resilience_data.get("health", {})
        health_config = HealthConfig(
            enabled=health_data.get("enabled", True),
            check_interval_seconds=health_data.get("check_interval_seconds", 30),
            circuit_breaker_check=health_data.get("circuit_breaker_check", True),
            rate_limiter_check=health_data.get("rate_limiter_check", True),
            model_availability_check=health_data.get("model_availability_check", True)
        )
        
        self.config = ResilienceConfig(
            circuit_breakers=circuit_breakers,
            rate_limiters=rate_limiters,
            logging=logging_config,
            alerts=alerts_config,
            health=health_config
        )
    
    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreakerConfig]:
        """获取指定熔断器配置"""
        return self.config.circuit_breakers.get(name)
    
    def get_rate_limiter(self, name: str) -> Optional[RateLimiterConfig]:
        """获取指定限流器配置"""
        return self.config.rate_limiters.get(name)
    
    def reload(self):
        """重新加载配置（热重载）"""
        print("Reloading resilience configuration...")
        self._load_config()
        return self.config


# 全局单例
_resilience_config_manager: Optional[ResilienceConfigManager] = None


def get_resilience_config() -> ResilienceConfigManager:
    """获取全局配置管理器"""
    global _resilience_config_manager
    if _resilience_config_manager is None:
        _resilience_config_manager = ResilienceConfigManager()
    return _resilience_config_manager
