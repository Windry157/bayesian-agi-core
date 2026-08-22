#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
向量索引功能测试脚本
验证Phase 4优化：向量索引集成
"""

import asyncio
import shutil
import os

from src.core.memory.memory_system import MemorySystem


async def test_vector_index():
    print("=== 测试向量索引功能 ===")
    
    test_dir = "test_memory_vector"
    
    # 清理之前的测试目录
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir, ignore_errors=True)
    
    # 创建记忆系统实例
    mem = MemorySystem(memory_dir=test_dir, use_vector_index=True)
    await mem.load()
    
    # 添加测试记忆
    await mem.add_memory("人工智能是研究、开发用于模拟、延伸和扩展人的智能的理论、方法、技术及应用系统的一门新的技术科学")
    await mem.add_memory("机器学习是人工智能的核心，是使计算机具有智能的根本途径")
    await mem.add_memory("深度学习是机器学习的一个分支，使用多层神经网络来模拟人脑的学习过程")
    await mem.add_memory("自然语言处理是人工智能的一个重要方向，让计算机能够理解和生成人类语言")
    await mem.add_memory("计算机视觉是人工智能的一个领域，让计算机能够理解和分析图像和视频")
    
    print(f"添加记忆完成，共 {mem.get_memory_count()} 条")
    
    # 测试语义检索 - 神经网络（默认阈值0.3）
    results = await mem.retrieve_memories("神经网络", top_k=3)
    print("\n语义检索结果 (神经网络, 阈值0.3):")
    for i, r in enumerate(results):
        print(f"{i+1}. 相似度: {r['score']:.4f}")
        print(f"   内容: {r['content']}")
    
    # 测试语义检索 - 语言理解（降低阈值）
    results = await mem.retrieve_memories("语言理解", top_k=3)
    print("\n语义检索结果 (语言理解, 阈值0.3):")
    for i, r in enumerate(results):
        print(f"{i+1}. 相似度: {r['score']:.4f}")
        print(f"   内容: {r['content']}")
    
    # 测试语义检索 - 图像识别（提高阈值）
    results = await mem.retrieve_memories("图像识别", top_k=3)
    print("\n语义检索结果 (图像识别, 阈值0.3):")
    for i, r in enumerate(results):
        print(f"{i+1}. 相似度: {r['score']:.4f}")
        print(f"   内容: {r['content']}")
    
    # 测试不同阈值效果对比
    print("\n=== 阈值效果对比 ===")
    for threshold in [0.0, 0.2, 0.4, 0.6]:
        results = await mem.retrieve_memories("神经网络", top_k=5)
        print(f"阈值 {threshold}: 找到 {len(results)} 条匹配")
    
    # 测试文本匹配检索（回退方案）
    results = await mem.retrieve_memories("机器学习", top_k=3, use_semantic=False)
    print("\n文本匹配检索结果 (机器学习):")
    for i, r in enumerate(results):
        print(f"{i+1}. 相似度: {r['score']:.4f}")
        print(f"   内容: {r['content']}")
    
    # 刷新并关闭
    await mem.flush()
    mem.close()
    
    # 清理测试目录
    shutil.rmtree(test_dir, ignore_errors=True)
    print("\n测试完成！")


if __name__ == "__main__":
    asyncio.run(test_vector_index())
