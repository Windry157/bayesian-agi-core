#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识图谱功能测试脚本
"""

import asyncio
import shutil
import os

from src.core.memory.memory_system import MemorySystem


async def test_knowledge_graph():
    print("=== 测试知识图谱功能 ===")
    
    test_dir = "test_knowledge_graph"
    
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir, ignore_errors=True)
    
    # 创建记忆系统（启用知识图谱）
    mem = MemorySystem(memory_dir=test_dir, use_knowledge_graph=True, use_vector_index=False)
    await mem.load()
    
    # 添加包含实体的记忆
    print("\n=== 添加记忆（包含实体）===")
    
    mem_id1 = await mem.add_memory("2024年5月，张三在阿里巴巴工作，负责深度学习项目")
    print(f"添加记忆1: {mem_id1}")
    
    mem_id2 = await mem.add_memory("深度学习是机器学习的一个分支，使用神经网络进行模式识别")
    print(f"添加记忆2: {mem_id2}")
    
    mem_id3 = await mem.add_memory("阿里巴巴是一家位于杭州的科技公司，成立于1999年")
    print(f"添加记忆3: {mem_id3}")
    
    # 测试实体抽取结果
    print("\n=== 查看知识图谱 ===")
    if mem.knowledge_graph:
        print(f"实体数量: {mem.knowledge_graph.get_entity_count()}")
        print(f"关系数量: {mem.knowledge_graph.get_relation_count()}")
    
    # 测试获取实体关系
    print("\n=== 获取实体关系 ===")
    relations = await mem.get_entity_relations("深度学习")
    print(f"'深度学习' 相关关系: {len(relations)} 条")
    for rel in relations:
        print(f"  {rel['source'][:8]}... -{rel['relation']}-> {rel['target'][:8]}...")
    
    # 测试知识推理
    print("\n=== 知识推理测试 ===")
    inferences = await mem.infer_knowledge("张三和阿里巴巴的关系")
    print(f"推理结果: {len(inferences)} 条")
    for inf in inferences:
        print(f"  {inf.get('source', '')} - {inf.get('relation', '')} -> {inf.get('target', '')} (置信度: {inf.get('confidence', 0)})")
    
    # 保存知识图谱
    await mem.save_knowledge_graph()
    await mem.flush()
    
    mem.close()
    
    # 清理测试目录
    shutil.rmtree(test_dir, ignore_errors=True)
    print("\n测试完成！")


if __name__ == "__main__":
    asyncio.run(test_knowledge_graph())
