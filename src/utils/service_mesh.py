#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务网格模块
负责服务间通信、流量管理和安全配置
"""

import logging
import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ServiceMesh:
    """服务网格
    
    负责服务间通信、流量管理和安全配置
    """
    
    def __init__(self):
        """初始化服务网格"""
        # 服务配置
        self.service_configs: Dict[str, Dict[str, Any]] = {}
        # 流量规则
        self.traffic_rules: List[Dict[str, Any]] = []
        # 安全策略
        self.security_policies: Dict[str, Dict[str, Any]] = {}
        # 服务健康状态
        self.service_health: Dict[str, Dict[str, Any]] = {}
        # 流量统计
        self.traffic_stats: Dict[str, Dict[str, Any]] = {}
        
        logger.info("服务网格初始化完成")
    
    def register_service(self, service_name: str, config: Dict[str, Any]):
        """注册服务
        
        Args:
            service_name: 服务名称
            config: 服务配置
        """
        self.service_configs[service_name] = {
            **config,
            "registered_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }
        
        # 初始化服务健康状态
        self.service_health[service_name] = {
            "status": "unknown",
            "last_check": datetime.now().isoformat(),
            "response_time": 0
        }
        
        # 初始化流量统计
        self.traffic_stats[service_name] = {
            "requests_total": 0,
            "errors_total": 0,
            "request_rate": 0,
            "error_rate": 0
        }
        
        logger.info(f"服务注册: {service_name}")
    
    def unregister_service(self, service_name: str):
        """注销服务
        
        Args:
            service_name: 服务名称
        """
        if service_name in self.service_configs:
            del self.service_configs[service_name]
            
        if service_name in self.service_health:
            del self.service_health[service_name]
        
        if service_name in self.traffic_stats:
            del self.traffic_stats[service_name]
        
        logger.info(f"服务注销: {service_name}")
    
    def add_traffic_rule(self, rule: Dict[str, Any]):
        """添加流量规则
        
        Args:
            rule: 流量规则
        """
        self.traffic_rules.append({
            **rule,
            "created_at": datetime.now().isoformat()
        })
        logger.info(f"添加流量规则: {rule.get('name', 'unnamed')}")
    
    def remove_traffic_rule(self, rule_name: str):
        """删除流量规则
        
        Args:
            rule_name: 规则名称
        """
        self.traffic_rules = [
            rule for rule in self.traffic_rules 
            if rule.get('name') != rule_name
        ]
        logger.info(f"删除流量规则: {rule_name}")
    
    def set_security_policy(self, service_name: str, policy: Dict[str, Any]):
        """设置安全策略
        
        Args:
            service_name: 服务名称
            policy: 安全策略
        """
        self.security_policies[service_name] = {
            **policy,
            "updated_at": datetime.now().isoformat()
        }
        logger.info(f"设置安全策略: {service_name}")
    
    def get_service_config(self, service_name: str) -> Optional[Dict[str, Any]]:
        """获取服务配置
        
        Args:
            service_name: 服务名称
            
        Returns:
            服务配置
        """
        return self.service_configs.get(service_name)
    
    def update_service_health(self, service_name: str, status: str, response_time: float):
        """更新服务健康状态
        
        Args:
            service_name: 服务名称
            status: 健康状态
            response_time: 响应时间
        """
        if service_name in self.service_health:
            self.service_health[service_name].update({
                "status": status,
                "last_check": datetime.now().isoformat(),
                "response_time": response_time
            })
        else:
            self.service_health[service_name] = {
                "status": status,
                "last_check": datetime.now().isoformat(),
                "response_time": response_time
            }
    
    def record_traffic(self, service_name: str, success: bool):
        """记录流量
        
        Args:
            service_name: 服务名称
            success: 是否成功
        """
        if service_name not in self.traffic_stats:
            self.traffic_stats[service_name] = {
                "requests_total": 0,
                "errors_total": 0,
                "request_rate": 0,
                "error_rate": 0
            }
        
        self.traffic_stats[service_name]["requests_total"] += 1
        if not success:
            self.traffic_stats[service_name]["errors_total"] += 1
        
        # 计算错误率
        total = self.traffic_stats[service_name]["requests_total"]
        errors = self.traffic_stats[service_name]["errors_total"]
        self.traffic_stats[service_name]["error_rate"] = errors / total if total > 0 else 0
    
    def get_service_health(self, service_name: str) -> Optional[Dict[str, Any]]:
        """获取服务健康状态
        
        Args:
            service_name: 服务名称
            
        Returns:
            服务健康状态
        """
        return self.service_health.get(service_name)
    
    def get_traffic_stats(self, service_name: str) -> Optional[Dict[str, Any]]:
        """获取流量统计
        
        Args:
            service_name: 服务名称
            
        Returns:
            流量统计
        """
        return self.traffic_stats.get(service_name)
    
    def get_all_services(self) -> Dict[str, Dict[str, Any]]:
        """获取所有服务
        
        Returns:
            服务列表
        """
        return self.service_configs
    
    def get_all_traffic_rules(self) -> List[Dict[str, Any]]:
        """获取所有流量规则
        
        Returns:
            流量规则列表
        """
        return self.traffic_rules
    
    def get_all_security_policies(self) -> Dict[str, Dict[str, Any]]:
        """获取所有安全策略
        
        Returns:
            安全策略列表
        """
        return self.security_policies
    
    def get_service_mesh_status(self) -> Dict[str, Any]:
        """获取服务网格状态
        
        Returns:
            服务网格状态
        """
        return {
            "services": {
                service: {
                    "config": self.service_configs.get(service),
                    "health": self.service_health.get(service),
                    "traffic": self.traffic_stats.get(service)
                }
                for service in self.service_configs
            },
            "traffic_rules": self.traffic_rules,
            "security_policies": self.security_policies,
            "total_services": len(self.service_configs),
            "total_rules": len(self.traffic_rules),
            "timestamp": datetime.now().isoformat()
        }


# 全局服务网格实例
service_mesh = ServiceMesh()
