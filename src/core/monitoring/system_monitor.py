"""
系统监控 - 监控系统资源使用情况
"""
import time
import asyncio
from dataclasses import dataclass
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    """系统指标"""
    cpu_percent: float
    memory_percent: float
    memory_used: int
    memory_total: int
    disk_percent: float
    disk_used: int
    disk_total: int
    timestamp: float
    
    def to_dict(self) -> Dict:
        return {
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'memory_used': self.memory_used,
            'memory_total': self.memory_total,
            'memory_used_mb': round(self.memory_used / (1024 * 1024), 2),
            'memory_total_mb': round(self.memory_total / (1024 * 1024), 2),
            'disk_percent': self.disk_percent,
            'disk_used': self.disk_used,
            'disk_total': self.disk_total,
            'disk_used_mb': round(self.disk_used / (1024 * 1024), 2),
            'disk_total_mb': round(self.disk_total / (1024 * 1024), 2),
            'timestamp': self.timestamp
        }

class SystemMonitor:
    """系统监控器"""
    
    def __init__(self, metrics_collector=None):
        self.metrics_collector = metrics_collector
        self._running = False
        self._monitor_task = None
        self._psutil = None
        
    async def initialize(self):
        """初始化"""
        try:
            import psutil
            self._psutil = psutil
            logger.info("✅ psutil 已加载，系统监控可用")
        except ImportError:
            logger.warning("⚠️ psutil 未安装，部分系统监控功能不可用")
            self._psutil = None
            
    async def get_system_metrics(self) -> SystemMetrics:
        """获取系统指标"""
        cpu_percent = 0.0
        memory_percent = 0.0
        memory_used = 0
        memory_total = 1
        disk_percent = 0.0
        disk_used = 0
        disk_total = 1
        
        if self._psutil:
            try:
                cpu_percent = self._psutil.cpu_percent(interval=0.1)
            except Exception as e:
                logger.debug(f"⚠️ 获取 CPU 使用率失败: {e}")
                
            try:
                memory = self._psutil.virtual_memory()
                memory_percent = memory.percent
                memory_used = memory.used
                memory_total = memory.total
            except Exception as e:
                logger.debug(f"⚠️ 获取内存使用失败: {e}")
                
            try:
                import os
                disk = self._psutil.disk_usage(os.path.dirname(__file__))
                disk_percent = disk.percent
                disk_used = disk.used
                disk_total = disk.total
            except Exception as e:
                logger.debug(f"⚠️ 获取磁盘使用失败: {e}")
                
        metrics = SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used=memory_used,
            memory_total=memory_total,
            disk_percent=disk_percent,
            disk_used=disk_used,
            disk_total=disk_total,
            timestamp=time.time()
        )
        
        if self.metrics_collector:
            await self.metrics_collector.gauge('system.cpu.percent', cpu_percent)
            await self.metrics_collector.gauge('system.memory.percent', memory_percent)
            await self.metrics_collector.gauge('system.memory.used', memory_used)
            await self.metrics_collector.gauge('system.disk.percent', disk_percent)
            
        return metrics
        
    async def start(self, interval: int = 5):
        """启动监控"""
        if self._running:
            return
            
        await self.initialize()
        self._running = True
        logger.info("🚀 系统监控已启动")
        
        async def monitor_loop():
            while self._running:
                try:
                    await self.get_system_metrics()
                except Exception as e:
                    logger.error(f"⚠️ 系统监控采集失败: {e}")
                await asyncio.sleep(interval)
                
        self._monitor_task = asyncio.create_task(monitor_loop())
        
    async def stop(self):
        """停止监控"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("👋 系统监控已停止")
