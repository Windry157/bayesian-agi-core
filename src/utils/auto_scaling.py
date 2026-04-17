#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动扩缩容模块
负责根据系统负载动态调整服务实例的数量
"""

import logging
import asyncio
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AutoScalingManager:
    """自动扩缩容管理器
    
    负责根据系统负载动态调整服务实例的数量
    """
    
    def __init__(self):
        """初始化自动扩缩容管理器"""
        # 服务扩缩容配置
        self.scaling_configs: Dict[str, Dict[str, Any]] = {}
        # 服务当前实例数
        self.service_instances: Dict[str, int] = {}
        # 服务负载历史
        self.load_history: Dict[str, List[Dict[str, Any]]] = {}
        # 扩缩容事件历史
        self.scaling_events: List[Dict[str, Any]] = []
        # 运行状态
        self.running = False
        # 检查任务
        self.check_task = None
        # 检查间隔（秒）
        self.check_interval = 30
        
        logger.info("自动扩缩容管理器初始化完成")
    
    async def start(self):
        """启动自动扩缩容管理器"""
        if not self.running:
            self.running = True
            self.check_task = asyncio.create_task(self._scaling_check_loop())
            logger.info("自动扩缩容管理器启动")
    
    async def stop(self):
        """停止自动扩缩容管理器"""
        if self.running:
            self.running = False
            if self.check_task:
                self.check_task.cancel()
                try:
                    await self.check_task
                except asyncio.CancelledError:
                    pass
            logger.info("自动扩缩容管理器停止")
    
    async def _scaling_check_loop(self):
        """扩缩容检查循环"""
        while self.running:
            try:
                await self.check_scaling()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"扩缩容检查循环错误: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def check_scaling(self):
        """检查扩缩容"""
        for service_name, config in self.scaling_configs.items():
            try:
                # 获取服务负载
                load = await self._get_service_load(service_name)
                
                # 记录负载历史
                self._record_load_history(service_name, load)
                
                # 计算平均负载
                avg_load = self._calculate_average_load(service_name)
                
                # 检查是否需要扩缩容
                current_instances = self.service_instances.get(service_name, 1)
                desired_instances = self._calculate_desired_instances(service_name, avg_load)
                
                if desired_instances != current_instances:
                    await self._scale_service(service_name, desired_instances)
            except Exception as e:
                logger.error(f"检查服务{service_name}扩缩容失败: {e}")
    
    async def _get_service_load(self, service_name: str) -> float:
        """获取服务负载
        
        Args:
            service_name: 服务名称
            
        Returns:
            服务负载
        """
        # 模拟负载获取
        # 实际应用中应该从监控系统获取真实负载
        import random
        return random.uniform(0.1, 1.0)
    
    def _record_load_history(self, service_name: str, load: float):
        """记录负载历史
        
        Args:
            service_name: 服务名称
            load: 负载
        """
        if service_name not in self.load_history:
            self.load_history[service_name] = []
        
        self.load_history[service_name].append({
            "timestamp": datetime.now().isoformat(),
            "load": load
        })
        
        # 保留最近10分钟的负载历史
        cutoff_time = datetime.now().timestamp() - 600
        self.load_history[service_name] = [
            entry for entry in self.load_history[service_name]
            if datetime.fromisoformat(entry["timestamp"]).timestamp() > cutoff_time
        ]
    
    def _calculate_average_load(self, service_name: str) -> float:
        """计算平均负载
        
        Args:
            service_name: 服务名称
            
        Returns:
            平均负载
        """
        if service_name not in self.load_history or not self.load_history[service_name]:
            return 0.5
        
        loads = [entry["load"] for entry in self.load_history[service_name]]
        return sum(loads) / len(loads)
    
    def _calculate_desired_instances(self, service_name: str, avg_load: float) -> int:
        """计算期望的实例数
        
        Args:
            service_name: 服务名称
            avg_load: 平均负载
            
        Returns:
            期望的实例数
        """
        config = self.scaling_configs.get(service_name, {})
        min_instances = config.get("min_instances", 1)
        max_instances = config.get("max_instances", 5)
        target_load = config.get("target_load", 0.7)
        
        # 计算期望实例数
        desired = max(min_instances, min(max_instances, int(round(avg_load / target_load)))
        
        return desired
    
    async def _scale_service(self, service_name: str, desired_instances: int):
        """扩缩容服务
        
        Args:
            service_name: 服务名称
            desired_instances: 期望的实例数
        """
        current_instances = self.service_instances.get(service_name, 1)
        
        if desired_instances > current_instances:
            # 扩容
            logger.info(f"扩容服务 {service_name}: {current_instances} -> {desired_instances}")
            # 实际应用中应该启动新的服务实例
        elif desired_instances < current_instances:
            # 缩容
            logger.info(f"缩容服务 {service_name}: {current_instances} -> {desired_instances}")
            # 实际应用中应该停止多余的服务实例
        
        # 更新实例数
        self.service_instances[service_name] = desired_instances
        
        # 记录扩缩容事件
        self.scaling_events.append({
            "timestamp": datetime.now().isoformat(),
            "service": service_name,
            "from_instances": current_instances,
            "to_instances": desired_instances,
            "reason": "auto_scaling"
        })
        
        # 保留最近100个扩缩容事件
        if len(self.scaling_events) > 100:
            self.scaling_events = self.scaling_events[-100:]
    
    def set_scaling_config(self, service_name: str, config: Dict[str, Any]):
        """设置扩缩容配置
        
        Args:
            service_name: 服务名称
            config: 扩缩容配置
        """
        default_config = {
            "min_instances": 1,
            "max_instances": 5,
            "target_load": 0.7,
            "scale_up_threshold": 0.8,
            "scale_down_threshold": 0.4
        }
        
        self.scaling_configs[service_name] = {**default_config, **config}
        
        # 初始化实例数
        if service_name not in self.service_instances:
            self.service_instances[service_name] = config.get("min_instances", 1)
        
        logger.info(f"设置服务{service_name}的扩缩容配置: {self.scaling_configs[service_name]}")
    
    def get_scaling_config(self, service_name: str) -> Optional[Dict[str, Any]]:
        """获取扩缩容配置
        
        Args:
            service_name: 服务名称
            
        Returns:
            扩缩容配置
        """
        return self.scaling_configs.get(service_name)
    
    def get_service_instances(self, service_name: str) -> int:
        """获取服务实例数
        
        Args:
            service_name: 服务名称
            
        Returns:
            实例数
        """
        return self.service_instances.get(service_name, 1)
    
    def get_load_history(self, service_name: str) -> List[Dict[str, Any]]:
        """获取负载历史
        
        Args:
            service_name: 服务名称
            
        Returns:
            负载历史
        """
        return self.load_history.get(service_name, [])
    
    def get_scaling_events(self) -> List[Dict[str, Any]]:
        """获取扩缩容事件
        
        Returns:
            扩缩容事件
        """
        return self.scaling_events
    
    def get_auto_scaling_status(self) -> Dict[str, Any]:
        """获取自动扩缩容状态
        
        Returns:
            自动扩缩容状态
        """
        return {
            "services": {
                service: {
                    "config": self.scaling_configs.get(service),
                    "instances": self.service_instances.get(service, 1),
                    "load_history": self.load_history.get(service, [])
                }
                for service in self.scaling_configs
            },
            "scaling_events": self.scaling_events,
            "running": self.running,
            "check_interval": self.check_interval,
            "timestamp": datetime.now().isoformat()
        }
    
    def set_check_interval(self, interval: int):
        """设置检查间隔
        
        Args:
            interval: 间隔（秒）
        """
        if interval > 0:
            self.check_interval = interval
            logger.info(f"检查间隔设置为: {interval}秒")


# 全局自动扩缩容管理器实例
auto_scaling_manager = AutoScalingManager()
