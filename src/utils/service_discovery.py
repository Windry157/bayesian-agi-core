#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务发现和负载均衡模块
负责服务的注册、发现和负载均衡
"""

import logging
import asyncio
import random
from typing import Dict, List, Optional, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ServiceDiscovery:
    """服务发现和负载均衡
    
    负责服务的注册、发现和负载均衡
    """
    
    def __init__(self):
        """初始化服务发现模块"""
        # 服务注册表
        self.services: Dict[str, List[Dict[str, Any]]] = {
            "llm_service": [],
            "memory_service": [],
            "cognition_service": [],
            "vision_service": [],
            "multimodal_service": []
        }
        # 服务健康状态
        self.service_health: Dict[str, Dict[str, bool]] = {}
        # 服务权重
        self.service_weights: Dict[str, Dict[str, float]] = {}
        # 服务调用计数
        self.service_calls: Dict[str, Dict[str, int]] = {}
        
        logger.info("服务发现模块初始化完成")
    
    def register_service(self, service_name: str, service_url: str, weight: float = 1.0):
        """注册服务
        
        Args:
            service_name: 服务名称
            service_url: 服务URL
            weight: 服务权重
        """
        if service_name not in self.services:
            self.services[service_name] = []
        
        # 检查是否已存在
        for service in self.services[service_name]:
            if service["url"] == service_url:
                logger.warning(f"服务已注册: {service_name} - {service_url}")
                return
        
        # 添加服务
        self.services[service_name].append({
            "url": service_url,
            "weight": weight,
            "last_health_check": None,
            "status": "unknown"
        })
        
        # 初始化健康状态
        if service_name not in self.service_health:
            self.service_health[service_name] = {}
        self.service_health[service_name][service_url] = True
        
        # 初始化权重
        if service_name not in self.service_weights:
            self.service_weights[service_name] = {}
        self.service_weights[service_name][service_url] = weight
        
        # 初始化调用计数
        if service_name not in self.service_calls:
            self.service_calls[service_name] = {}
        self.service_calls[service_name][service_url] = 0
        
        logger.info(f"注册服务: {service_name} - {service_url} (权重: {weight})")
    
    def deregister_service(self, service_name: str, service_url: str):
        """注销服务
        
        Args:
            service_name: 服务名称
            service_url: 服务URL
        """
        if service_name in self.services:
            self.services[service_name] = [
                service for service in self.services[service_name] 
                if service["url"] != service_url
            ]
            
            # 更新健康状态
            if service_name in self.service_health and service_url in self.service_health[service_name]:
                del self.service_health[service_name][service_url]
            
            # 更新权重
            if service_name in self.service_weights and service_url in self.service_weights[service_name]:
                del self.service_weights[service_name][service_url]
            
            # 更新调用计数
            if service_name in self.service_calls and service_url in self.service_calls[service_name]:
                del self.service_calls[service_name][service_url]
            
            logger.info(f"注销服务: {service_name} - {service_url}")
    
    def get_service_url(self, service_name: str) -> Optional[str]:
        """获取服务URL（负载均衡）
        
        Args:
            service_name: 服务名称
            
        Returns:
            服务URL
        """
        if service_name not in self.services or not self.services[service_name]:
            logger.warning(f"服务不存在或无可用实例: {service_name}")
            return None
        
        # 过滤健康的服务
        healthy_services = []
        for service in self.services[service_name]:
            url = service["url"]
            if self.service_health.get(service_name, {}).get(url, False):
                healthy_services.append(service)
        
        if not healthy_services:
            logger.warning(f"无健康的服务实例: {service_name}")
            # 返回任意一个服务作为降级方案
            if self.services[service_name]:
                return self.services[service_name][0]["url"]
            return None
        
        # 基于权重和调用计数的负载均衡
        total_weight = sum(service["weight"] for service in healthy_services)
        
        if total_weight <= 0:
            # 随机选择
            selected = random.choice(healthy_services)
        else:
            # 基于权重的随机选择
            r = random.uniform(0, total_weight)
            current = 0
            selected = None
            
            for service in healthy_services:
                current += service["weight"]
                if current >= r:
                    selected = service
                    break
            
            if not selected:
                selected = healthy_services[0]
        
        # 更新调用计数
        url = selected["url"]
        if service_name in self.service_calls:
            self.service_calls[service_name][url] = self.service_calls[service_name].get(url, 0) + 1
        
        logger.debug(f"选择服务: {service_name} - {url}")
        return url
    
    def update_service_health(self, service_name: str, service_url: str, is_healthy: bool):
        """更新服务健康状态
        
        Args:
            service_name: 服务名称
            service_url: 服务URL
            is_healthy: 是否健康
        """
        if service_name not in self.service_health:
            self.service_health[service_name] = {}
        
        old_status = self.service_health[service_name].get(service_url, False)
        if old_status != is_healthy:
            status = "健康" if is_healthy else "不健康"
            logger.info(f"服务状态更新: {service_name} - {service_url} - {status}")
        
        self.service_health[service_name][service_url] = is_healthy
    
    def get_service_health(self, service_name: str) -> Dict[str, bool]:
        """获取服务健康状态
        
        Args:
            service_name: 服务名称
            
        Returns:
            服务健康状态
        """
        return self.service_health.get(service_name, {})
    
    def get_service_statistics(self, service_name: str) -> Dict[str, Any]:
        """获取服务统计信息
        
        Args:
            service_name: 服务名称
            
        Returns:
            服务统计信息
        """
        return {
            "total_instances": len(self.services.get(service_name, [])),
            "healthy_instances": sum(1 for is_healthy in self.service_health.get(service_name, {}).values() if is_healthy),
            "calls": self.service_calls.get(service_name, {})
        }
    
    def list_services(self) -> Dict[str, List[Dict[str, Any]]]:
        """列出所有服务
        
        Returns:
            服务列表
        """
        return self.services
    
    def clear(self):
        """清空服务注册表"""
        self.services = {
            "llm_service": [],
            "memory_service": [],
            "cognition_service": [],
            "vision_service": [],
            "multimodal_service": []
        }
        self.service_health = {}
        self.service_weights = {}
        self.service_calls = {}
        logger.info("服务注册表已清空")


# 全局服务发现实例
service_discovery = ServiceDiscovery()
