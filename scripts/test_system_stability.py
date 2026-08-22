#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统稳定性测试 - 验证记忆系统优化后的稳定性
"""

import sys
import os
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.memory.memory_system import MemorySystem


def generate_test_content(index):
    """生成测试内容"""
    topics = ["AI", "机器学习", "深度学习", "NLP", "计算机视觉", "强化学习", "大数据", "云计算"]
    topic = topics[index % len(topics)]
    return f"这是关于{topic}的测试记忆内容，编号{index}。"


async def test_stability():
    """运行稳定性测试"""
    print("[测试开始] 系统稳定性验证")
    print("="*60)
    
    errors = []
    success_count = 0
    total_tests = 10
    
    # 测试1: 基础功能测试
    print("\n[测试1/10] 基础功能测试")
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            ms = MemorySystem(memory_dir=temp_dir)
            await ms.load()
            
            # 添加记忆
            mem_id = await ms.add_memory("测试记忆内容")
            assert mem_id is not None
            assert ms.get_memory_count() == 1
            
            # 检索记忆
            results = await ms.retrieve_memories("测试")
            assert len(results) == 1
            assert results[0]["id"] == mem_id
            
            # 清除记忆
            await ms.clear_memory()
            assert ms.get_memory_count() == 0
            
        print("  [OK] 通过")
        success_count += 1
    except Exception as e:
        print(f"  [FAIL] 失败: {e}")
        errors.append(f"测试1失败: {e}")
    
    # 测试2: 批量操作测试
    print("\n[测试2/10] 批量操作测试")
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            ms = MemorySystem(memory_dir=temp_dir)
            await ms.load()
            
            # 批量添加100条
            contents = [generate_test_content(i) for i in range(100)]
            mem_ids = await ms.add_batch(contents)
            assert len(mem_ids) == 100
            assert ms.get_memory_count() == 100
            
        print("  [OK] 通过")
        success_count += 1
    except Exception as e:
        print(f"  [FAIL] 失败: {e}")
        errors.append(f"测试2失败: {e}")
    
    # 测试3: 并发添加测试
    print("\n[测试3/10] 并发添加测试")
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            ms = MemorySystem(memory_dir=temp_dir)
            await ms.load()
            
            async def add_task(content):
                await ms.add_memory(content)
            
            # 并发添加20条
            tasks = [add_task(f"并发测试内容{i}") for i in range(20)]
            await asyncio.gather(*tasks)
            
            assert ms.get_memory_count() == 20
            
        print("  [OK] 通过")
        success_count += 1
    except Exception as e:
        print(f"  [FAIL] 失败: {e}")
        errors.append(f"测试3失败: {e}")
    
    # 测试4: 检索功能测试
    print("\n[测试4/10] 检索功能测试")
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            ms = MemorySystem(memory_dir=temp_dir)
            await ms.load()
            
            # 添加不同主题的记忆
            await ms.add_batch([
                "机器学习入门教程",
                "深度学习神经网络",
                "NLP自然语言处理",
                "计算机视觉图像识别",
                "强化学习策略优化"
            ])
            
            # 测试不同查询词
            results = await ms.retrieve_memories("学习")
            assert len(results) >= 2
            
            results = await ms.retrieve_memories("视觉")
            assert len(results) >= 1
            
        print("  [OK] 通过")
        success_count += 1
    except Exception as e:
        print(f"  [FAIL] 失败: {e}")
        errors.append(f"测试4失败: {e}")
    
    # 测试5: 持久化测试
    print("\n[测试5/10] 持久化测试")
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # 第一次创建并添加
            ms1 = MemorySystem(memory_dir=temp_dir)
            await ms1.load()
            await ms1.add_batch(["持久化测试记忆1", "持久化测试记忆2"])
            await ms1.flush()
            count1 = ms1.get_memory_count()
            
            # 创建新实例加载
            ms2 = MemorySystem(memory_dir=temp_dir)
            await ms2.load()
            count2 = ms2.get_memory_count()
            
            assert count1 == count2 == 2
            
        print("  [OK] 通过")
        success_count += 1
    except Exception as e:
        print(f"  [FAIL] 失败: {e}")
        errors.append(f"测试5失败: {e}")
    
    # 测试6: 边界条件测试
    print("\n[测试6/10] 边界条件测试")
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            ms = MemorySystem(memory_dir=temp_dir)
            await ms.load()
            
            # 空内容
            mem_id = await ms.add_memory("")
            assert mem_id is not None
            
            # 长内容
            long_content = "A" * 10000
            mem_id = await ms.add_memory(long_content)
            assert mem_id is not None
            
            # 特殊字符
            special_content = "测试特殊字符: 中文 🎉 @#$%^&*()"
            mem_id = await ms.add_memory(special_content)
            assert mem_id is not None
            
        print("  [OK] 通过")
        success_count += 1
    except Exception as e:
        print(f"  [FAIL] 失败: {e}")
        errors.append(f"测试6失败: {e}")
    
    # 测试7: 缓冲区刷新测试
    print("\n[测试7/10] 缓冲区刷新测试")
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            ms = MemorySystem(memory_dir=temp_dir, buffer_size=10)
            await ms.load()
            
            # 添加少于缓冲区大小的记忆
            for i in range(5):
                await ms.add_memory(f"缓冲测试{i}")
            
            # 手动刷新
            await ms.flush()
            
            # 验证数据
            ms2 = MemorySystem(memory_dir=temp_dir)
            await ms2.load()
            assert ms2.get_memory_count() == 5
            
        print("  [OK] 通过")
        success_count += 1
    except Exception as e:
        print(f"  [FAIL] 失败: {e}")
        errors.append(f"测试7失败: {e}")
    
    # 测试8: 上下文管理器测试
    print("\n[测试8/10] 上下文管理器测试")
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            async with MemorySystem(memory_dir=temp_dir) as ms:
                await ms.load()
                await ms.add_memory("上下文管理器测试")
            
            # 验证数据持久化
            ms2 = MemorySystem(memory_dir=temp_dir)
            await ms2.load()
            assert ms2.get_memory_count() == 1
            
        print("  [OK] 通过")
        success_count += 1
    except Exception as e:
        print(f"  [FAIL] 失败: {e}")
        errors.append(f"测试8失败: {e}")
    
    # 测试9: 元数据测试
    print("\n[测试9/10] 元数据测试")
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            ms = MemorySystem(memory_dir=temp_dir)
            await ms.load()
            
            metadata = {"source": "test", "tags": ["ai", "test"]}
            mem_id = await ms.add_memory("带元数据的记忆", metadata=metadata)
            
            # 检索并验证元数据
            results = await ms.retrieve_memories("元数据")
            assert len(results) == 1
            assert results[0]["metadata"]["source"] == "test"
            
        print("  [OK] 通过")
        success_count += 1
    except Exception as e:
        print(f"  [FAIL] 失败: {e}")
        errors.append(f"测试9失败: {e}")
    
    # 测试10: 性能稳定性测试
    print("\n[测试10/10] 性能稳定性测试")
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            ms = MemorySystem(memory_dir=temp_dir)
            await ms.load()
            
            start = datetime.now()
            # 添加200条记忆
            contents = [generate_test_content(i) for i in range(200)]
            await ms.add_batch(contents)
            
            # 执行多次检索
            for i in range(10):
                await ms.retrieve_memories("学习")
            
            elapsed = (datetime.now() - start).total_seconds()
            
            assert ms.get_memory_count() == 200
            assert elapsed < 5  # 应该在5秒内完成
            
            print(f"  完成时间: {elapsed:.2f}秒")
            print("  [OK] 通过")
            success_count += 1
    except Exception as e:
        print(f"  [FAIL] 失败: {e}")
        errors.append(f"测试10失败: {e}")
    
    # 总结
    print("\n" + "="*60)
    print("[测试完成] 稳定性测试总结")
    print(f"  通过: {success_count}/{total_tests}")
    print(f"  失败: {len(errors)}/{total_tests}")
    
    if errors:
        print("\n[错误详情]")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
    
    return success_count == total_tests


if __name__ == "__main__":
    success = asyncio.run(test_stability())
    exit(0 if success else 1)
