"""
缓存指标统计
"""
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

@dataclass
class CacheMetrics:
    """缓存指标统计"""
    total_hits: int = 0
    total_misses: int = 0
    total_sets: int = 0
    total_deletes: int = 0
    total_errors: int = 0
    hit_rate: float = 0.0
    operation_times: Dict[str, List[float]] = field(default_factory=dict)
    operation_counts: Dict[str, int] = field(default_factory=dict)
    
    def record_hit(self):
        """记录缓存命中"""
        self.total_hits += 1
        self._update_hit_rate()
        
    def record_miss(self):
        """记录缓存未命中"""
        self.total_misses += 1
        self._update_hit_rate()
        
    def record_set(self):
        """记录缓存写入"""
        self.total_sets += 1
        
    def record_delete(self):
        """记录缓存删除"""
        self.total_deletes += 1
        
    def record_error(self):
        """记录错误"""
        self.total_errors += 1
        
    def record_operation_time(self, operation: str, duration: float):
        """记录操作耗时"""
        if operation not in self.operation_times:
            self.operation_times[operation] = []
        self.operation_times[operation].append(duration)
        
        if len(self.operation_times[operation]) > 1000:
            self.operation_times[operation].pop(0)
            
        if operation not in self.operation_counts:
            self.operation_counts[operation] = 0
        self.operation_counts[operation] += 1
        
    def _update_hit_rate(self):
        """更新命中率"""
        total = self.total_hits + self.total_misses
        if total > 0:
            self.hit_rate = self.total_hits / total
        else:
            self.hit_rate = 0.0
            
    def get_average_time(self, operation: str) -> Optional[float]:
        """获取平均操作耗时"""
        times = self.operation_times.get(operation, [])
        if times:
            return sum(times) / len(times)
        return None
        
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'total_hits': self.total_hits,
            'total_misses': self.total_misses,
            'total_sets': self.total_sets,
            'total_deletes': self.total_deletes,
            'total_errors': self.total_errors,
            'hit_rate': round(self.hit_rate * 100, 2),
            'operation_averages': {
                op: round(self.get_average_time(op) or 0.0, 4)
                for op in self.operation_times
            },
            'operation_counts': self.operation_counts
        }
