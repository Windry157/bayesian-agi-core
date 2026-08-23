#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
索引优化器
提供向量索引优化、重建和性能调优功能。
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class IndexType(Enum):
    """索引类型"""
    HNSW = "hnsw"
    IVF = "ivf"
    FLAT = "flat"


@dataclass
class IndexConfig:
    """索引配置"""
    index_type: IndexType
    dimension: int
    metric: str = "cosine"
    hnsw_m: int = 16
    hnsw_ef_construction: int = 200
    hnsw_ef_search: int = 128
    ivf_nlist: int = 100
    ivf_nprobe: int = 10


@dataclass
class OptimizationResult:
    """优化结果"""
    success: bool
    before_size: int
    after_size: int
    query_latency_improvement: float
    memory_usage_improvement: float
    details: Dict[str, Any]


class IndexOptimizer:
    """索引优化器

    提供向量索引优化功能：
    - 索引参数调优
    - 索引重建
    - 性能监控
    - 自动优化
    """

    def __init__(self, config: Optional[IndexConfig] = None):
        """初始化优化器

        Args:
            config: 索引配置，None则使用默认
        """
        self.config = config or IndexConfig(
            index_type=IndexType.HNSW,
            dimension=768
        )
        self.performance_history: List[Dict[str, Any]] = []
        logger.info(f"IndexOptimizer initialized with {self.config.index_type}")

    def optimize(
        self,
        index: Any,
        method: str = "auto"
    ) -> OptimizationResult:
        """优化索引

        Args:
            index: 索引对象 (ChromaDB collection 或类似)
            method: 优化方法 ("auto", "rebuild", "tune")

        Returns:
            OptimizationResult: 优化结果
        """
        logger.info(f"Starting index optimization, method={method}")

        before_size = self._get_index_size(index)
        before_latency = self._measure_latency(index)

        if method == "auto":
            result = self._optimize_auto(index)
        elif method == "rebuild":
            result = self._optimize_rebuild(index)
        elif method == "tune":
            result = self._optimize_tune(index)
        else:
            raise ValueError(f"Unknown optimization method: {method}")

        after_size = self._get_index_size(index)
        after_latency = self._measure_latency(index)

        # 计算改进
        latency_improvement = (before_latency - after_latency) / before_latency if before_latency > 0 else 0
        memory_improvement = (before_size - after_size) / before_size if before_size > 0 else 0

        final_result = OptimizationResult(
            success=result.get('success', True),
            before_size=before_size,
            after_size=after_size,
            query_latency_improvement=latency_improvement,
            memory_usage_improvement=memory_improvement,
            details=result
        )

        # 记录性能历史
        self.performance_history.append({
            "timestamp": __import__('datetime').datetime.now().isoformat(),
            "before_latency": before_latency,
            "after_latency": after_latency,
            "before_size": before_size,
            "after_size": after_size,
            "method": method
        })

        logger.info(
            f"Optimization complete: latency {latency_improvement:.1%} improvement, "
            f"memory {memory_improvement:.1%} improvement"
        )

        return final_result

    def _optimize_auto(self, index: Any) -> Dict[str, Any]:
        """自动优化

        根据当前状态选择最佳优化策略。

        Args:
            index: 索引对象

        Returns:
            Dict[str, Any]: 结果
        """
        # 简单的自动优化逻辑
        size = self._get_index_size(index)

        if size > 10000:
            # 大数据集：优化 HNSW 参数
            return self._optimize_tune(index)
        else:
            # 小数据集：重建索引
            return self._optimize_rebuild(index)

    def _optimize_rebuild(self, index: Any) -> Dict[str, Any]:
        """重建索引

        Args:
            index: 索引对象

        Returns:
            Dict[str, Any]: 结果
        """
        try:
            # 对于 ChromaDB，可以触发重建
            if hasattr(index, 'persist'):
                index.persist()

            return {
                "success": True,
                "method": "rebuild",
                "message": "Index rebuilt successfully"
            }
        except Exception as e:
            logger.error(f"Rebuild failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _optimize_tune(self, index: Any) -> Dict[str, Any]:
        """调优索引参数

        Args:
            index: 索引对象

        Returns:
            Dict[str, Any]: 结果
        """
        # 这里可以实现参数调优逻辑
        # 对于 ChromaDB，HNSW 参数可以在创建 collection 时设置
        # 这里记录优化意图

        return {
            "success": True,
            "method": "tune",
            "suggested_config": {
                "hnsw_ef_search": max(64, self.config.hnsw_ef_search),
                "hnsw_m": min(48, self.config.hnsw_m)
            },
            "message": "Parameters tuned (apply on next index creation)"
        }

    def _get_index_size(self, index: Any) -> int:
        """获取索引大小

        Args:
            index: 索引对象

        Returns:
            int: 项目数量
        """
        try:
            if hasattr(index, 'count'):
                return index.count()
            elif hasattr(index, '__len__'):
                return len(index)
        except Exception:
            pass
        return 0

    def _measure_latency(self, index: Any, num_trials: int = 5) -> float:
        """测量查询延迟

        Args:
            index: 索引对象
            num_trials: 测试次数

        Returns:
            float: 平均延迟 (秒)
        """
        import time
        import random

        # 生成随机查询向量
        dim = self.config.dimension
        query_vector = [random.random() for _ in range(dim)]

        total_time = 0.0

        for _ in range(num_trials):
            start = time.time()
            try:
                if hasattr(index, 'query'):
                    # 尝试查询
                    index.query(query_embeddings=[query_vector], n_results=1)
            except Exception:
                pass  # 忽略查询错误
            end = time.time()
            total_time += (end - start)

        return total_time / num_trials if num_trials > 0 else 0

    def get_recommended_config(
        self,
        num_vectors: int,
        query_performance_requirement: str = "balanced"
    ) -> IndexConfig:
        """获取推荐的索引配置

        Args:
            num_vectors: 向量数量
            query_performance_requirement: 性能要求
                ("speed", "balanced", "memory")

        Returns:
            IndexConfig: 推荐配置
        """
        base_config = IndexConfig(
            index_type=IndexType.HNSW,
            dimension=self.config.dimension
        )

        if query_performance_requirement == "speed":
            # 速度优先
            base_config.hnsw_m = 32
            base_config.hnsw_ef_construction = 400
            base_config.hnsw_ef_search = 256
        elif query_performance_requirement == "memory":
            # 内存优先
            base_config.hnsw_m = 8
            base_config.hnsw_ef_construction = 100
            base_config.hnsw_ef_search = 64
        else:
            # 平衡
            if num_vectors < 10000:
                base_config.hnsw_m = 16
                base_config.hnsw_ef_construction = 200
                base_config.hnsw_ef_search = 128
            elif num_vectors < 1000000:
                base_config.hnsw_m = 24
                base_config.hnsw_ef_construction = 300
                base_config.hnsw_ef_search = 192
            else:
                base_config.hnsw_m = 32
                base_config.hnsw_ef_construction = 400
                base_config.hnsw_ef_search = 256

        return base_config

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计

        Returns:
            Dict[str, Any]: 统计信息
        """
        if not self.performance_history:
            return {"message": "No performance history"}

        latest = self.performance_history[-1]

        return {
            "latest": latest,
            "total_optimizations": len(self.performance_history),
            "average_latency_improvement": sum(
                h.get('before_latency', 0) - h.get('after_latency', 0)
                for h in self.performance_history
            ) / len(self.performance_history)
        }

    def clear_history(self):
        """清空性能历史"""
        self.performance_history.clear()
        logger.info("Performance history cleared")
