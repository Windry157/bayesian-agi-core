#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高可用配置模块
负责管理服务的高可用设置和故障转移策略
"""

import logging
import asyncio
import time
from typing import Dict, List, Optional, Any
from .service_discovery import service_discovery
from .http_client import http_client_manager

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class HighAvailabilityManager:
    """高可用管理器
    
    负责管理服务的高可用设置和故障转移策略
    """
    
    def __init__(self):
        """初始化高可用管理器"""
        # 健康检查间隔（秒）
        self.health_check_interval = 10
        # 服务恢复检查间隔（秒）
        self.recovery_check_interval = 30
        # 故障转移策略
        self.failover_strategy = "round_robin"
        # 健康检查超时（秒）
        self.health_check_timeout = 5
        # 服务重试次数
        self.service_retry_count = 3
        # 服务重试间隔（秒）
        self.service_retry_interval = 1
        # 健康检查任务
        self.health_check_task = None
        # 运行状态
        self.running = False
        
        logger.info("高可用管理器初始化完成")
    
    async def start(self):
        """启动高可用管理器"""
        if not self.running:
            self.running = True
            self.health_check_task = asyncio.create_task(self._health_check_loop())
            logger.info("高可用管理器启动")
    
    async def stop(self):
        """停止高可用管理器"""
        if self.running:
            self.running = False
            if self.health_check_task:
                self.health_check_task.cancel()
                try:
                    await self.health_check_task
                except asyncio.CancelledError:
                    pass
            logger.info("高可用管理器停止")
    
    async def _health_check_loop(self):
        """健康检查循环"""
        while self.running:
            try:
                await self.perform_health_checks()
                await asyncio.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"健康检查循环错误: {e}")
                await asyncio.sleep(self.health_check_interval)
    
    async def perform_health_checks(self):
        """执行健康检查"""
        services = service_discovery.list_services()
        
        for service_name, instances in services.items():
            for instance in instances:
                service_url = instance["url"]
                is_healthy = await self._check_service_health(service_url)
                service_discovery.update_service_health(service_name, service_url, is_healthy)
    
    async def _check_service_health(self, service_url: str) -> bool:
        """检查服务健康状态
        
        Args:
            service_url: 服务URL
            
        Returns:
            是否健康
        """
        try:
            client = await http_client_manager.get_client(service_url)
            response = await asyncio.wait_for(
                client.get("/health"),
                timeout=self.health_check_timeout
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"服务健康检查失败: {service_url} - {e}")
            return False
    
    async def execute_with_failover(self, service_name: str, method: str, endpoint: str, **kwargs) -> Optional[Any]:
        """执行带故障转移的服务调用
        
        Args:
            service_name: 服务名称
            method: HTTP方法
            endpoint: 端点
            **kwargs: 其他参数
            
        Returns:
            服务响应
        """
        retries = 0
        last_error = None
        
        while retries < self.service_retry_count:
            try:
                # 获取服务URL
                service_url = service_discovery.get_service_url(service_name)
                if not service_url:
                    raise Exception(f"无可用的{service_name}服务实例")
                
                # 构建完整URL
                url = f"{service_url}{endpoint}"
                
                # 获取HTTP客户端
                client = await http_client_manager.get_client(service_url)
                
                # 执行请求
                if method.upper() == "GET":
                    response = await client.get(endpoint, **kwargs)
                elif method.upper() == "POST":
                    response = await client.post(endpoint, **kwargs)
                elif method.upper() == "PUT":
                    response = await client.put(endpoint, **kwargs)
                elif method.upper() == "DELETE":
                    response = await client.delete(endpoint, **kwargs)
                else:
                    raise Exception(f"不支持的HTTP方法: {method}")
                
                # 检查响应状态
                if response.status_code < 500:
                    return response
                else:
                    logger.warning(f"服务{service_name}返回错误状态码: {response.status_code}")
                    # 标记服务为不健康
                    service_discovery.update_service_health(service_name, service_url, False)
                    last_error = Exception(f"服务返回错误状态码: {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"服务{service_name}调用失败: {e}")
                last_error = e
            
            # 重试
            retries += 1
            if retries < self.service_retry_count:
                logger.info(f"重试服务{service_name}调用 ({retries}/{self.service_retry_count})")
                await asyncio.sleep(self.service_retry_interval)
        
        # 所有重试都失败
        logger.error(f"服务{service_name}调用失败，所有重试都已用尽")
        raise last_error if last_error else Exception(f"服务{service_name}调用失败")
    
    def set_health_check_interval(self, interval: int):
        """设置健康检查间隔
        
        Args:
            interval: 间隔（秒）
        """
        if interval > 0:
            self.health_check_interval = interval
            logger.info(f"健康检查间隔设置为: {interval}秒")
    
    def set_failover_strategy(self, strategy: str):
        """设置故障转移策略
        
        Args:
            strategy: 策略名称
        """
        valid_strategies = ["round_robin", "weighted", "least_connections"]
        if strategy in valid_strategies:
            self.failover_strategy = strategy
            logger.info(f"故障转移策略设置为: {strategy}")
        else:
            logger.warning(f"无效的故障转移策略: {strategy}")
    
    def get_service_availability(self) -> Dict[str, Dict[str, Any]]:
        """获取服务可用性信息
        
        Returns:
            服务可用性信息
        """
        availability = {}
        services = service_discovery.list_services()
        
        for service_name, instances in services.items():
            stats = service_discovery.get_service_statistics(service_name)
            health = service_discovery.get_service_health(service_name)
            
            availability[service_name] = {
                "total_instances": stats["total_instances"],
                "healthy_instances": stats["healthy_instances"],
                "availability_rate": stats["healthy_instances"] / stats["total_instances"] if stats["total_instances"] > 0 else 0,
                "health_status": health,
                "calls": stats["calls"]
            }
        
        return availability
    
    def register_service_instance(self, service_name: str, service_url: str, weight: float = 1.0):
        """注册服务实例
        
        Args:
            service_name: 服务名称
            service_url: 服务URL
            weight: 服务权重
        """
        service_discovery.register_service(service_name, service_url, weight)
    
    def deregister_service_instance(self, service_name: str, service_url: str):
        """注销服务实例
        
        Args:
            service_name: 服务名称
            service_url: 服务URL
        """
        service_discovery.deregister_service(service_name, service_url)


# 全局高可用管理器实例
high_availability_manager = HighAvailabilityManager()
