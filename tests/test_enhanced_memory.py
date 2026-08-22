#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强记忆模块测试
"""

import pytest
from datetime import datetime, timedelta
from src.core.memory.memory_compressor import (
    MemoryCompressor,
    CompressionResult
)
from src.core.memory.lifecycle_manager import (
    MemoryLifecycleManager,
    MemoryLayer,
    LayerConfig,
    LifecycleEvent
)
from src.core.memory.index_optimizer import (
    IndexOptimizer,
    IndexType,
    IndexConfig,
    OptimizationResult
)


class TestMemoryCompressor:
    """记忆压缩器测试"""
    
    def test_compressor_initialization(self):
        """测试压缩器初始化"""
        compressor = MemoryCompressor(similarity_threshold=0.85)
        
        assert compressor.similarity_threshold == 0.85
    
    def test_compute_fingerprint(self):
        """测试指纹计算"""
        compressor = MemoryCompressor()
        
        text1 = "这是关于机器学习的测试内容"
        text2 = "这是关于机器学习的测试内容"
        
        fp1 = compressor._compute_fingerprint(text1)
        fp2 = compressor._compute_fingerprint(text2)
        
        # 相同内容应该有相同指纹
        assert fp1 == fp2
    
    def test_compress_by_similarity(self):
        """测试基于相似度压缩"""
        compressor = MemoryCompressor()
        
        memories = [
            {
                "id": "m1",
                "content": "机器学习是人工智能的一个分支",
                "importance": 0.8,
                "access_count": 5,
                "created_at": datetime.now().isoformat()
            },
            {
                "id": "m2",
                "content": "机器学习是AI的一个分支领域",
                "importance": 0.7,
                "access_count": 3,
                "created_at": datetime.now().isoformat()
            },
            {
                "id": "m3",
                "content": "深度学习是机器学习的子领域",
                "importance": 0.9,
                "access_count": 10,
                "created_at": datetime.now().isoformat()
            }
        ]
        
        result = compressor.compress(memories, strategy="similarity")
        
        assert isinstance(result, CompressionResult)
        assert result.original_count == 3
    
    def test_compress_by_importance(self):
        """测试基于重要性压缩"""
        compressor = MemoryCompressor()
        
        memories = []
        for i in range(10):
            memories.append({
                "id": f"m{i}",
                "content": f"记忆内容 {i}",
                "importance": i * 0.1,
                "access_count": i,
                "created_at": datetime.now().isoformat()
            })
        
        result = compressor.compress(memories, strategy="importance", keep_ratio=0.5)
        
        assert result.compressed_count <= 5
    
    def test_merge_memories(self):
        """测试合并记忆"""
        compressor = MemoryCompressor()
        
        memories = [
            {
                "id": "m1",
                "content": "内容A",
                "importance": 0.6,
                "metadata": {"source": "test"}
            },
            {
                "id": "m2",
                "content": "内容B",
                "importance": 0.8,
                "metadata": {"author": "user"}
            }
        ]
        
        merged = compressor._merge_memories(memories)
        
        assert "内容A" in merged["content"]
        assert "内容B" in merged["content"]
        assert merged["importance"] >= 0.6


class TestMemoryLifecycleManager:
    """生命周期管理器测试"""
    
    def test_manager_initialization(self):
        """测试管理器初始化"""
        manager = MemoryLifecycleManager()
        
        assert manager.configs is not None
        assert MemoryLayer.SHORT_TERM in manager.configs
        assert MemoryLayer.MEDIUM_TERM in manager.configs
        assert MemoryLayer.LONG_TERM in manager.configs
    
    def test_custom_config(self):
        """测试自定义配置"""
        custom_configs = {
            MemoryLayer.SHORT_TERM: LayerConfig(
                capacity=50,
                retention_hours=12,
                promotion_threshold=0.6,
                demotion_threshold=0.0
            )
        }
        
        manager = MemoryLifecycleManager(configs=custom_configs)
        
        assert manager.configs[MemoryLayer.SHORT_TERM].capacity == 50
    
    def test_should_promote(self):
        """测试晋升判断"""
        manager = MemoryLifecycleManager()
        
        memory = {
            "id": "m1",
            "importance": 0.9,
            "access_count": 15
        }
        
        # 高重要性应该晋升
        assert manager.should_promote(memory, MemoryLayer.SHORT_TERM) is True
    
    def test_should_demote(self):
        """测试降级判断"""
        manager = MemoryLifecycleManager()
        
        old_date = (datetime.now() - timedelta(days=30)).isoformat()
        
        memory = {
            "id": "m1",
            "importance": 0.2,
            "last_accessed": old_date
        }
        
        # 低重要性且很久未访问应该降级
        assert manager.should_demote(memory, MemoryLayer.MEDIUM_TERM) is True
    
    def test_should_expire(self):
        """测试过期判断"""
        manager = MemoryLifecycleManager()
        
        old_date = (datetime.now() - timedelta(days=100)).isoformat()
        
        memory = {
            "id": "m1",
            "importance": 0.1,
            "created_at": old_date
        }
        
        assert manager.should_expire(memory, MemoryLayer.SHORT_TERM) is True
    
    def test_get_next_layer(self):
        """测试获取下一层级"""
        manager = MemoryLifecycleManager()
        
        assert manager.get_next_layer(MemoryLayer.SHORT_TERM) == MemoryLayer.MEDIUM_TERM
        assert manager.get_next_layer(MemoryLayer.MEDIUM_TERM) == MemoryLayer.LONG_TERM
        assert manager.get_next_layer(MemoryLayer.LONG_TERM) is None
    
    def test_get_previous_layer(self):
        """测试获取上一层级"""
        manager = MemoryLifecycleManager()
        
        assert manager.get_previous_layer(MemoryLayer.LONG_TERM) == MemoryLayer.MEDIUM_TERM
        assert manager.get_previous_layer(MemoryLayer.MEDIUM_TERM) == MemoryLayer.SHORT_TERM
        assert manager.get_previous_layer(MemoryLayer.SHORT_TERM) is None
    
    def test_process_lifecycle(self):
        """测试生命周期处理"""
        manager = MemoryLifecycleManager()
        
        memories_by_layer = {
            MemoryLayer.SHORT_TERM: [
                {
                    "id": "m1",
                    "content": "重要记忆",
                    "importance": 0.9,
                    "access_count": 20,
                    "created_at": datetime.now().isoformat()
                }
            ],
            MemoryLayer.MEDIUM_TERM: [],
            MemoryLayer.LONG_TERM: []
        }
        
        result = manager.process_lifecycle(memories_by_layer)
        
        assert "promoted" in result
        assert len(manager.events) > 0
    
    def test_enforce_capacity(self):
        """测试容量限制"""
        manager = MemoryLifecycleManager()
        
        memories = []
        for i in range(200):
            memories.append({
                "id": f"m{i}",
                "content": f"内容 {i}",
                "importance": i / 200,
                "last_accessed": datetime.now().isoformat()
            })
        
        filtered = manager.enforce_capacity(memories, MemoryLayer.SHORT_TERM)
        
        # 短期记忆默认容量100
        assert len(filtered) <= 100


class TestIndexOptimizer:
    """索引优化器测试"""
    
    def test_optimizer_initialization(self):
        """测试优化器初始化"""
        optimizer = IndexOptimizer()
        
        assert optimizer.config is not None
        assert optimizer.config.index_type == IndexType.HNSW
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = IndexConfig(
            index_type=IndexType.HNSW,
            dimension=512,
            metric="cosine",
            hnsw_m=24,
            hnsw_ef_construction=300
        )
        
        optimizer = IndexOptimizer(config=config)
        
        assert optimizer.config.dimension == 512
        assert optimizer.config.hnsw_m == 24
    
    def test_get_recommended_config_small(self):
        """测试小数据集推荐配置"""
        optimizer = IndexOptimizer()
        
        config = optimizer.get_recommended_config(
            num_vectors=5000,
            query_performance_requirement="balanced"
        )
        
        assert config.index_type == IndexType.HNSW
    
    def test_get_recommended_config_large(self):
        """测试大数据集推荐配置"""
        optimizer = IndexOptimizer()
        
        config = optimizer.get_recommended_config(
            num_vectors=2000000,
            query_performance_requirement="speed"
        )
        
        assert config.hnsw_m >= 24
    
    def test_get_recommended_config_memory(self):
        """测试内存优先配置"""
        optimizer = IndexOptimizer()
        
        config = optimizer.get_recommended_config(
            num_vectors=100000,
            query_performance_requirement="memory"
        )
        
        assert config.hnsw_m <= 16
    
    def test_performance_history(self):
        """测试性能历史"""
        optimizer = IndexOptimizer()
        
        # 模拟添加性能记录
        optimizer.performance_history.append({
            "timestamp": datetime.now().isoformat(),
            "before_latency": 0.1,
            "after_latency": 0.05,
            "before_size": 1000,
            "after_size": 1000,
            "method": "tune"
        })
        
        stats = optimizer.get_performance_stats()
        
        assert stats["total_optimizations"] == 1
    
    def test_clear_history(self):
        """测试清空历史"""
        optimizer = IndexOptimizer()
        
        optimizer.performance_history.append({
            "timestamp": datetime.now().isoformat()
        })
        
        optimizer.clear_history()
        
        assert len(optimizer.performance_history) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
