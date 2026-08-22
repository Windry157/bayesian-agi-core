"""
指标收集器 - 收集系统运行指标
"""
import time
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)

@dataclass
class Metric:
    """指标数据点"""
    name: str
    value: float
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)
    type: str = "gauge"  # gauge, counter, histogram

@dataclass
class TimeWindowMetric:
    """时间窗口指标"""
    name: str
    window_seconds: int
    data_points: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    def add_point(self, value: float, timestamp: float, tags: Dict[str, str] = None):
        """添加数据点"""
        self.data_points.append(Metric(
            name=self.name,
            value=value,
            timestamp=timestamp,
            tags=tags or {}
        ))
        
    def get_average(self) -> Optional[float]:
        """获取平均值"""
        if not self.data_points:
            return None
        return sum(p.value for p in self.data_points) / len(self.data_points)
        
    def get_min(self) -> Optional[float]:
        """获取最小值"""
        if not self.data_points:
            return None
        return min(p.value for p in self.data_points)
        
    def get_max(self) -> Optional[float]:
        """获取最大值"""
        if not self.data_points:
            return None
        return max(p.value for p in self.data_points)
        
    def get_latest(self) -> Optional[Metric]:
        """获取最新值"""
        if not self.data_points:
            return None
        return self.data_points[-1]

class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self._metrics: Dict[str, TimeWindowMetric] = {}
        self._counters: Dict[str, int] = defaultdict(int)
        self._histograms: Dict[str, deque] = {}
        self._lock = asyncio.Lock()
        self._callbacks: List[Callable] = []
        
    async def increment(self, name: str, value: int = 1, tags: Dict[str, str] = None):
        """增加计数器"""
        async with self._lock:
            self._counters[name] += value
            timestamp = time.time()
            
            if name not in self._metrics:
                self._metrics[name] = TimeWindowMetric(name, window_seconds=3600)
            self._metrics[name].add_point(self._counters[name], timestamp, tags)
            
            await self._trigger_callbacks()
            
    async def gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """设置仪表盘指标"""
        async with self._lock:
            timestamp = time.time()
            
            if name not in self._metrics:
                self._metrics[name] = TimeWindowMetric(name, window_seconds=3600)
            self._metrics[name].add_point(value, timestamp, tags)
            
            await self._trigger_callbacks()
            
    async def histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        """记录直方图数据"""
        async with self._lock:
            if name not in self._histograms:
                self._histograms[name] = deque(maxlen=1000)
            self._histograms[name].append(value)
            
            if name not in self._metrics:
                self._metrics[name] = TimeWindowMetric(name, window_seconds=3600)
            self._metrics[name].add_point(value, time.time(), tags)
            
            await self._trigger_callbacks()
            
    async def timing(self, name: str, tags: Dict[str, str] = None):
        """计时装饰器"""
        start_time = time.time()
        
        class Timer:
            def __init__(self, collector, name, tags):
                self.collector = collector
                self.name = name
                self.tags = tags
                self.start_time = time.time()
                
            async def __aenter__(self):
                return self
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                duration = time.time() - self.start_time
                await self.collector.histogram(self.name, duration, self.tags)
                await self.collector.gauge(f"{self.name}.duration", duration, self.tags)
                
        return Timer(self, name, tags)
        
    async def record_api_request(self, endpoint: str, duration: float, status_code: int):
        """记录 API 请求"""
        tags = {'endpoint': endpoint, 'status': str(status_code)}
        await self.increment('api.requests.total', tags=tags)
        await self.histogram('api.requests.duration', duration, tags=tags)
        
        if status_code >= 400:
            await self.increment('api.requests.errors', tags=tags)
            
    async def get_metric(self, name: str) -> Optional[TimeWindowMetric]:
        """获取指标"""
        return self._metrics.get(name)
        
    async def get_all_metrics(self) -> Dict[str, Dict]:
        """获取所有指标统计"""
        async with self._lock:
            result = {}
            for name, metric in self._metrics.items():
                result[name] = {
                    'latest': metric.get_latest().value if metric.get_latest() else None,
                    'average': metric.get_average(),
                    'min': metric.get_min(),
                    'max': metric.get_max(),
                    'count': len(metric.data_points),
                    'type': 'time_window'
                }
                
            for name, value in self._counters.items():
                if name not in result:
                    result[name] = {}
                result[name]['counter'] = value
                result[name]['type'] = 'counter'
                
            return result
            
    def register_callback(self, callback: Callable):
        """注册指标变更回调"""
        self._callbacks.append(callback)
        
    async def _trigger_callbacks(self):
        """触发回调"""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(self)
                else:
                    callback(self)
            except Exception as e:
                logger.error(f"⚠️ 指标回调执行失败: {e}")
                
    async def clear(self):
        """清空所有指标"""
        async with self._lock:
            self._metrics.clear()
            self._counters.clear()
            self._histograms.clear()
