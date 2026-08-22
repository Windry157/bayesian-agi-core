#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
离线模式使用示例
"""

import os
import sys
import asyncio

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 设置环境变量启用离线模式
os.environ["OFFLINE_MODE"] = "true"
os.environ["OFFLINE_CONFIG"] = os.path.join(os.path.dirname(__file__), '..', 'config', 'offline-mode.json')

from src.utils.offline_support import offline_mode
from src.core.memory.memory_system import MemorySystem

async def main():
    print("=" * 60)
    print("Bayesian-AGI-Core 离线模式示例")
    print("=" * 60)
    
    # 检查离线模式状态
    print(f"\n离线模式状态: {'启用' if offline_mode.is_offline() else '禁用'}")
    
    # 初始化记忆系统（离线模式）
    print("\n初始化记忆系统（离线模式）...")
    memory = MemorySystem(
        memory_dir="example_offline_memory",
        use_vector_index=False,      # 禁用向量索引
        use_knowledge_graph=True,    # 启用知识图谱
        use_msgpack=True,            # 使用高效存储
        buffer_size=50
    )
    
    # 添加一些记忆
    print("\n添加记忆...")
    memories = [
        "Bayesian-AGI-Core 是一个基于自由能原理的智能体项目",
        "项目现在支持完全离线运行",
        "知识图谱模块使用规则抽取，不需要网络下载",
        "记忆系统有多层优化：缓冲、批量写入、MessagePack",
        "审计日志、权限管理、多租户都可以离线使用"
    ]
    
    for i, content in enumerate(memories):
        await memory.add_memory(
            content,
            metadata={
                "source": "offline_example",
                "index": i,
                "timestamp": str(asyncio.get_event_loop().time())
            }
        )
        print(f"  ✓ 添加记忆 {i+1}: {content[:30]}...")
    
    # 检索记忆
    print("\n检索记忆（关键词匹配）...")
    queries = ["离线", "记忆", "知识"]
    for query in queries:
        results = await memory.retrieve_memories(query, top_k=3)
        print(f"\n  查询: '{query}'")
        if results:
            for i, result in enumerate(results):
                if isinstance(result, dict):
                    content = result.get('content', str(result))[:40]
                else:
                    content = str(result)[:40]
                print(f"    {i+1}. {content}...")
        else:
            print(f"    无结果")
    
    # 手动刷新
    print("\n刷新到磁盘...")
    await memory.flush()
    print("  ✓ 刷新完成")
    
    # 显示统计
    print("\n" + "=" * 60)
    print("离线模式运行成功！")
    print("=" * 60)
    print("\n核心功能可用:")
    print("  ✓ 记忆添加/检索")
    print("  ✓ 知识图谱")
    print("  ✓ 批量操作")
    print("  ✓ 持久化存储")
    print("\n限制:")
    print("  ✗ 向量索引（使用关键词匹配替代）")
    print("  ✗ LLM 实体抽取（使用规则抽取替代）")

if __name__ == "__main__":
    asyncio.run(main())
