#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记忆权重管理和时效性衰减测试脚本
"""

import asyncio
import shutil
import os

from src.core.memory.memory_system import MemorySystem


async def test_memory_weight():
    print("=== 测试记忆权重管理系统 ===")
    
    test_dir = "test_memory_weight"
    
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir, ignore_errors=True)
    
    mem = MemorySystem(memory_dir=test_dir, use_vector_index=True)
    await mem.load()
    
    # 添加不同重要性的记忆
    mem_id1 = await mem.add_memory("神经网络是深度学习的基础", importance=3.0)  # 高重要性
    mem_id2 = await mem.add_memory("Python是一种流行的编程语言", importance=1.0)  # 普通重要性
    mem_id3 = await mem.add_memory("今天天气很好", importance=0.5)  # 低重要性
    mem_id4 = await mem.add_memory("深度学习是机器学习的分支", importance=2.5)  # 中高重要性
    
    print(f"\n添加4条记忆，重要性分别为: 3.0, 1.0, 0.5, 2.5")
    
    # 测试获取权重
    print("\n=== 初始权重 ===")
    for mid in [mem_id1, mem_id2, mem_id3, mem_id4]:
        weight = await mem.get_memory_weight(mid)
        print(f"记忆 {mid[:12]}... 权重: {weight:.4f}")
    
    # 测试语义检索（使用权重排序）
    print("\n=== 语义检索测试 (使用权重排序) ===")
    results = await mem.retrieve_memories("机器学习", top_k=3)
    for i, r in enumerate(results):
        print(f"{i+1}. 综合分数: {r.get('combined_score', 0.0):.4f}, 语义分数: {r.get('score', 0.0):.4f}, 权重: {r.get('weight', 1.0):.4f}")
        print(f"   内容: {r['content']}")
    
    # 测试设置重要性
    print("\n=== 设置重要性 ===")
    await mem.set_importance(mem_id3, 4.0)  # 将"今天天气很好"提升为高重要性
    weight = await mem.get_memory_weight(mem_id3)
    print(f"将 '今天天气很好' 的重要性设为 4.0，当前权重: {weight:.4f}")
    
    # 测试清理低权重记忆
    print("\n=== 清理低权重记忆测试 ===")
    await mem.prune_low_weight_memories(min_weight=0.1)
    print(f"清理后剩余记忆数: {mem.get_memory_count()}")
    
    # 测试时间衰减（模拟）
    print("\n=== 模拟时间衰减 ===")
    # 修改创建时间为30天前
    for mid in mem.memory_cache:
        mem.memory_cache[mid]["created_at"] = "2026-04-15T10:00:00"
    
    mem._apply_time_decay()
    
    print("模拟30天后的权重:")
    for mid in mem.memory_cache:
        weight = await mem.get_memory_weight(mid)
        importance = mem.memory_cache[mid].get("importance", 1.0)
        print(f"记忆 {mid[:12]}... 重要性={importance}, 30天后权重={weight:.4f}")
    
    await mem.flush()
    mem.close()
    
    shutil.rmtree(test_dir, ignore_errors=True)
    print("\n测试完成！")


if __name__ == "__main__":
    asyncio.run(test_memory_weight())
