#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控服务
负责定期收集系统性能数据和服务健康状态
"""

import os
import asyncio
import psutil
import logging
from typing import Dict, Any
from src.core.monitoring import monitoring
from src.utils.service_discovery import service_discovery
from src.utils.high_availability import high_availability_manager

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MonitoringService:
    """监控服务
    
    负责定期收集系统性能数据和服务健康状态
    """
    
    def __init__(self):
        """初始化监控服务"""
        # 收集间隔（秒）
        self.collection_interval = 10
        # 运行状态
        self.running = False
        # 收集任务
        self.collection_task = None
        
        logger.info("监控服务初始化完成")
    
    async def start(self):
        """启动监控服务"""
        if not self.running:
            self.running = True
            self.collection_task = asyncio.create_task(self._collection_loop())
            logger.info("监控服务启动")
    
    async def stop(self):
        """停止监控服务"""
        if self.running:
            self.running = False
            if self.collection_task:
                self.collection_task.cancel()
                try:
                    await self.collection_task
                except asyncio.CancelledError:
                    pass
            logger.info("监控服务停止")
    
    async def _collection_loop(self):
        """数据收集循环"""
        while self.running:
            try:
                await self.collect_system_metrics()
                await self.collect_service_health()
                await asyncio.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"数据收集循环错误: {e}")
                await asyncio.sleep(self.collection_interval)
    
    async def collect_system_metrics(self):
        """收集系统指标"""
        try:
            # 收集CPU使用率
            cpu_usage = psutil.cpu_percent(interval=1)
            monitoring.record_cpu_usage(cpu_usage)
            
            # 收集内存使用情况
            memory = psutil.virtual_memory()
            monitoring.record_memory_usage(memory.used)
            
            # 收集系统负载
            if hasattr(psutil, 'getloadavg'):
                load_avg = psutil.getloadavg()[0]
                monitoring.record_system_load(load_avg)
            
            # 收集磁盘使用情况
            disk = psutil.disk_usage('/')
            monitoring.record_disk_usage(disk.percent)
            
            logger.debug(f"系统指标收集完成: CPU={cpu_usage}%, 内存={memory.used/1024/1024:.2f}MB, 磁盘={disk.percent}%")
            
        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")
    
    async def collect_service_health(self):
        """收集服务健康状态"""
        try:
            # 获取服务可用性信息
            availability = high_availability_manager.get_service_availability()
            
            for service_name, info in availability.items():
                # 记录服务健康状态
                status = 1.0 if info["availability_rate"] > 0 else 0.0
                monitoring.record_service_health(service_name, status)
                
                # 异步记录服务健康状态
                await monitoring.async_record_service_health(service_name, status)
            
            logger.debug(f"服务健康状态收集完成: {availability}")
            
        except Exception as e:
            logger.error(f"收集服务健康状态失败: {e}")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态
        
        Returns:
            系统状态信息
        """
        try:
            # 收集系统信息
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # 获取服务可用性
            availability = high_availability_manager.get_service_availability()
            
            return {
                "system": {
                    "cpu_usage": cpu_usage,
                    "memory_usage": memory.used,
                    "memory_percent": memory.percent,
                    "disk_usage": disk.used,
                    "disk_percent": disk.percent,
                    "load_avg": psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0
                },
                "services": availability
            }
            
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {"error": str(e)}
    
    def set_collection_interval(self, interval: int):
        """设置收集间隔
        
        Args:
            interval: 间隔（秒）
        """
        if interval > 0:
            self.collection_interval = interval
            logger.info(f"收集间隔设置为: {interval}秒")


# 全局监控服务实例
monitoring_service = MonitoringService()
