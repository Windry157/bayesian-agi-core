#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记忆系统优化对比测试

测试优化前后的性能差异

Phase 1 优化内容:
- 内存写入缓冲
- add_batch() 批量方法
- flush() 手动刷新
"""

import sys
import os
import json
import time
import tempfile
import shutil
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def generate_test_data(num_items: int = 100) -> List[str]:
    """生成测试数据"""
    topics = ["AI", "机器学习", "深度学习", "NLP", "计算机视觉", "强化学习"]
    contents = []
    for i in range(num_items):
        topic = topics[i % len(topics)]
        content = f"这是关于{topic}的记忆内容，编号{i}。"
        contents.append(content)
    return contents


class OriginalMemorySystem:
    """原始版本（从备份中模拟）"""
    
    def __init__(self, memory_dir: str):
        self.memory_dir = memory_dir
        os.makedirs(self.memory_dir, exist_ok=True)
        self.memory_cache = {}
    
    async def load(self):
        self._load_from_disk()
    
    async def add_memory(self, content: str, metadata: Dict[str, Any] = None) -> str:
        memory_id = f"mem_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        self.memory_cache[memory_id] = {
            "id": memory_id,
            "content": content,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            "access_count": 1
        }
        self._save_to_disk()
        return memory_id
    
    async def retrieve_memories(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        results = []
        for memory_id, memory in self.memory_cache.items():
            if query.lower() in memory["content"].lower():
                results.append({
                    "id": memory["id"],
                    "content": memory["content"],
                    "score": 0.9
                })
        return results[:top_k]
    
    def _load_from_disk(self):
        memory_file = os.path.join(self.memory_dir, "memories.json")
        if os.path.exists(memory_file):
            with open(memory_file, 'r', encoding='utf-8') as f:
                self.memory_cache = json.load(f)
    
    def _save_to_disk(self):
        memory_file = os.path.join(self.memory_dir, "memories.json")
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(self.memory_cache, f, ensure_ascii=False, indent=2)


class OptimizedMemorySystem:
    """优化版本（直接引用）"""
    
    def __init__(self, memory_dir: str, buffer_size: int = 50):
        from src.core.memory.memory_system import MemorySystem
        self._system = MemorySystem(memory_dir=memory_dir, buffer_size=buffer_size)
    
    async def load(self):
        await self._system.load()
    
    async def add_memory(self, content: str, metadata: Dict[str, Any] = None) -> str:
        return await self._system.add_memory(content, metadata)
    
    async def add_batch(self, contents: List[str]) -> List[str]:
        return await self._system.add_batch(contents)
    
    def flush(self):
        self._system.flush()
    
    async def retrieve_memories(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        return await self._system.retrieve_memories(query, top_k)


async def run_test():
    """运行对比测试"""
    
    print("=" * 70)
    print("记忆系统优化对比测试")
    print("=" * 70)
    
    # 生成测试数据
    test_data_50 = generate_test_data(50)
    test_data_100 = generate_test_data(100)
    test_data_200 = generate_test_data(200)
    
    results = {}
    
    # 原始版本测试
    print("\n" + "=" * 70)
    print("1. 测试原始版本（立即写入磁盘）")
    print("=" * 70)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        orig_system = OriginalMemorySystem(temp_dir)
        await orig_system.load()
        
        # 测试50条
        start = time.time()
        for content in test_data_50:
            await orig_system.add_memory(content)
        orig_50_time = time.time() - start
        print(f"   添加50条: {orig_50_time:.4f}秒 ({50/orig_50_time:.1f}条/秒)")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        orig_system = OriginalMemorySystem(temp_dir)
        await orig_system.load()
        
        # 测试100条
        start = time.time()
        for content in test_data_100:
            await orig_system.add_memory(content)
        orig_100_time = time.time() - start
        print(f"   添加100条: {orig_100_time:.4f}秒 ({100/orig_100_time:.1f}条/秒)")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        orig_system = OriginalMemorySystem(temp_dir)
        await orig_system.load()
        
        # 测试200条
        start = time.time()
        for content in test_data_200:
            await orig_system.add_memory(content)
        orig_200_time = time.time() - start
        print(f"   添加200条: {orig_200_time:.4f}秒 ({200/orig_200_time:.1f}条/秒)")
    
    results["original"] = {
        "50_items": orig_50_time,
        "100_items": orig_100_time,
        "200_items": orig_200_time,
        "throughput_100": 100/orig_100_time
    }
    
    # 优化版本测试
    print("\n" + "=" * 70)
    print("2. 测试优化版本（缓冲写入）")
    print("=" * 70)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        opt_system = OptimizedMemorySystem(temp_dir, buffer_size=50)
        await opt_system.load()
        
        # 测试50条
        start = time.time()
        for content in test_data_50:
            await opt_system.add_memory(content)
        opt_system.flush()
        opt_50_time = time.time() - start
        print(f"   添加50条: {opt_50_time:.4f}秒 ({50/opt_50_time:.1f}条/秒)")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        opt_system = OptimizedMemorySystem(temp_dir, buffer_size=50)
        await opt_system.load()
        
        # 测试100条
        start = time.time()
        for content in test_data_100:
            await opt_system.add_memory(content)
        opt_system.flush()
        opt_100_time = time.time() - start
        print(f"   添加100条: {opt_100_time:.4f}秒 ({100/opt_100_time:.1f}条/秒)")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        opt_system = OptimizedMemorySystem(temp_dir, buffer_size=50)
        await opt_system.load()
        
        # 测试200条
        start = time.time()
        for content in test_data_200:
            await opt_system.add_memory(content)
        opt_system.flush()
        opt_200_time = time.time() - start
        print(f"   添加200条: {opt_200_time:.4f}秒 ({200/opt_200_time:.1f}条/秒)")
    
    results["optimized"] = {
        "50_items": opt_50_time,
        "100_items": opt_100_time,
        "200_items": opt_200_time,
        "throughput_100": 100/opt_100_time
    }
    
    # 优化版本-批量测试
    print("\n" + "=" * 70)
    print("3. 测试优化版本（批量添加）")
    print("=" * 70)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        opt_system = OptimizedMemorySystem(temp_dir, buffer_size=50)
        await opt_system.load()
        
        # 测试50条
        start = time.time()
        await opt_system.add_batch(test_data_50)
        batch_50_time = time.time() - start
        print(f"   批量50条: {batch_50_time:.4f}秒 ({50/batch_50_time:.1f}条/秒)")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        opt_system = OptimizedMemorySystem(temp_dir, buffer_size=50)
        await opt_system.load()
        
        # 测试100条
        start = time.time()
        await opt_system.add_batch(test_data_100)
        batch_100_time = time.time() - start
        print(f"   批量100条: {batch_100_time:.4f}秒 ({100/batch_100_time:.1f}条/秒)")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        opt_system = OptimizedMemorySystem(temp_dir, buffer_size=50)
        await opt_system.load()
        
        # 测试200条
        start = time.time()
        await opt_system.add_batch(test_data_200)
        batch_200_time = time.time() - start
        print(f"   批量200条: {batch_200_time:.4f}秒 ({200/batch_200_time:.1f}条/秒)")
    
    results["batch"] = {
        "50_items": batch_50_time,
        "100_items": batch_100_time,
        "200_items": batch_200_time,
        "throughput_100": 100/batch_100_time
    }
    
    # 检索性能测试
    print("\n" + "=" * 70)
    print("4. 测试检索性能")
    print("=" * 70)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        orig_system = OriginalMemorySystem(temp_dir)
        await orig_system.load()
        for content in test_data_100:
            await orig_system.add_memory(content)
        
        opt_system = OptimizedMemorySystem(temp_dir, buffer_size=50)
        await opt_system.load()
        
        # 测试原始版本检索
        queries = ["AI", "机器学习", "深度学习", "NLP", "计算机视觉"]
        start = time.time()
        for q in queries:
            await orig_system.retrieve_memories(q)
        orig_search_time = time.time() - start
        print(f"   原始版本检索: {orig_search_time:.4f}秒")
        
        # 测试优化版本检索
        start = time.time()
        for q in queries:
            await opt_system.retrieve_memories(q)
        opt_search_time = time.time() - start
        print(f"   优化版本检索: {opt_search_time:.4f}秒")
    
    results["search"] = {
        "original": orig_search_time,
        "optimized": opt_search_time
    }
    
    # 生成报告
    print("\n" + "=" * 70)
    print("性能对比总结")
    print("=" * 70)
    
    print(f"\n添加性能对比（100条）:")
    print(f"  原始版本:   {orig_100_time:.4f}秒, {100/orig_100_time:.1f}条/秒")
    print(f"  优化版本:   {opt_100_time:.4f}秒, {100/opt_100_time:.1f}条/秒")
    print(f"  批量版本:   {batch_100_time:.4f}秒, {100/batch_100_time:.1f}条/秒")
    
    improvement_opt = (orig_100_time - opt_100_time) / orig_100_time * 100
    improvement_batch = (orig_100_time - batch_100_time) / orig_100_time * 100
    
    print(f"\n性能提升:")
    print(f"  优化版本:   +{improvement_opt:.0f}% (速度提升 {(100/orig_100_time)/(100/opt_100_time):.1f}倍)")
    print(f"  批量版本:   +{improvement_batch:.0f}% (速度提升 {(100/orig_100_time)/(100/batch_100_time):.1f}倍)")
    
    # 保存结果
    report_file = project_root / "optimization_results.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存到: {report_file}")
    
    return results


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_test())
