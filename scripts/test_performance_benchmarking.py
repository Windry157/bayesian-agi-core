#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能基准测试框架
测试系统在不同场景下的性能表现
"""

import asyncio
import sys
import os
import time
import statistics

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.assistant import Assistant


async def benchmark_context_processing():
    """测试上下文处理性能"""
    print("测试 1: 上下文处理性能基准")
    
    assistant = Assistant()
    test_session_id = "test_context_performance"
    
    # 测试不同长度的输入
    test_inputs = [
        "你好",
        "请告诉我关于人工智能的最新进展",
        "计划一个周末去西雅图的旅行，重点关注历史景点，并提供预算明细。我喜欢历史和美食，预算有限，希望能有一个详细的行程安排。",
        "请帮我分析一下公司的财务状况。去年的总收入是1000万美元，支出是800万美元，利润是200万美元。今年的目标是增加20%的收入，同时降低10%的支出。请提供详细的分析和建议。"
    ]
    
    print("\n测试不同长度输入的处理时间...")
    
    for i, input_text in enumerate(test_inputs):
        times = []
        for _ in range(5):  # 每个输入测试5次
            start_time = time.time()
            await assistant.process_with_context(input_text, test_session_id)
            end_time = time.time()
            times.append(end_time - start_time)
        
        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"输入长度 {len(input_text)} 字符:")
        print(f"  平均时间: {avg_time:.4f}秒")
        print(f"  最短时间: {min_time:.4f}秒")
        print(f"  最长时间: {max_time:.4f}秒")
        print()
    
    print("✓ 上下文处理性能基准测试完成")
    print()


async def benchmark_memory_operations():
    """测试记忆操作性能"""
    print("测试 2: 记忆操作性能基准")
    
    assistant = Assistant()
    
    # 测试添加记忆
    print("\n测试添加记忆...")
    add_times = []
    for i in range(10):
        memory_content = f"测试记忆 {i}: 这是一个测试记忆内容，用于性能测试。" * (i % 3 + 1)
        start_time = time.time()
        await assistant.add_memory(memory_content, {"test": "performance"})
        end_time = time.time()
        add_times.append(end_time - start_time)
    
    avg_add_time = statistics.mean(add_times)
    print(f"平均添加记忆时间: {avg_add_time:.4f}秒")
    
    # 测试检索记忆
    print("\n测试检索记忆...")
    retrieve_times = []
    for i in range(5):
        start_time = time.time()
        await assistant.retrieve_memories("测试记忆", top_k=5)
        end_time = time.time()
        retrieve_times.append(end_time - start_time)
    
    avg_retrieve_time = statistics.mean(retrieve_times)
    print(f"平均检索记忆时间: {avg_retrieve_time:.4f}秒")
    
    print("✓ 记忆操作性能基准测试完成")
    print()


async def benchmark_meta_learning():
    """测试元学习性能"""
    print("测试 3: 元学习性能基准")
    
    assistant = Assistant()
    
    # 测试自我完善循环
    print("\n测试自我完善循环...")
    times = []
    for i in range(3):
        start_time = time.time()
        await assistant.self_improvement_cycle()
        end_time = time.time()
        times.append(end_time - start_time)
    
    if times:
        avg_time = statistics.mean(times)
        print(f"平均自我完善循环时间: {avg_time:.4f}秒")
    
    # 测试学习目标生成
    print("\n测试学习目标生成...")
    times = []
    for i in range(5):
        start_time = time.time()
        await assistant.generate_learning_goals()
        end_time = time.time()
        times.append(end_time - start_time)
    
    if times:
        avg_time = statistics.mean(times)
        print(f"平均学习目标生成时间: {avg_time:.4f}秒")
    
    print("✓ 元学习性能基准测试完成")
    print()


async def benchmark_concurrent_processing():
    """测试并发处理性能"""
    print("测试 4: 并发处理性能基准")
    
    assistant = Assistant()
    
    # 测试并发处理
    print("\n测试并发处理...")
    
    async def process_task(session_id, input_text):
        start_time = time.time()
        await assistant.process_with_context(input_text, session_id)
        end_time = time.time()
        return end_time - start_time
    
    # 创建多个并发任务
    tasks = []
    for i in range(5):
        session_id = f"test_concurrent_{i}"
        input_text = f"测试并发处理 {i}: 这是一个测试输入，用于并发性能测试。"
        tasks.append(process_task(session_id, input_text))
    
    start_time = time.time()
    times = await asyncio.gather(*tasks)
    total_time = time.time() - start_time
    
    avg_time = statistics.mean(times)
    print(f"总处理时间: {total_time:.4f}秒")
    print(f"平均任务时间: {avg_time:.4f}秒")
    print(f"并发效率: {total_time / avg_time:.2f}x")
    
    print("✓ 并发处理性能基准测试完成")
    print()


async def benchmark_long_term_coherence():
    """测试长期一致性性能"""
    print("测试 5: 长期一致性性能基准")
    
    assistant = Assistant()
    test_session_id = "test_long_term_performance"
    
    # 模拟多轮对话
    print("\n测试多轮对话性能...")
    
    prompts = [
        "我计划下个月去欧洲旅行",
        "推荐一些法国的历史景点",
        "这些景点的大致费用是多少？",
        "有没有便宜的住宿推荐？",
        "我还想去意大利",
        "帮我制定一个详细的行程",
        "需要考虑我的预算限制",
        "谢谢，这个计划很好"
    ]
    
    times = []
    for i, prompt in enumerate(prompts):
        start_time = time.time()
        await assistant.process_with_context(prompt, test_session_id)
        end_time = time.time()
        times.append(end_time - start_time)
        
        print(f"轮次 {i+1}: {times[-1]:.4f}秒")
    
    avg_time = statistics.mean(times)
    total_time = sum(times)
    
    print(f"\n总处理时间: {total_time:.4f}秒")
    print(f"平均轮次时间: {avg_time:.4f}秒")
    
    print("✓ 长期一致性性能基准测试完成")
    print()


async def benchmark_resource_usage():
    """测试资源使用情况"""
    print("测试 6: 资源使用基准")
    
    import psutil
    
    print("\n测试内存使用...")
    
    # 初始内存使用
    initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
    print(f"初始内存使用: {initial_memory:.2f} MB")
    
    # 创建助手实例
    assistant = Assistant()
    
    # 执行一些操作
    test_session_id = "test_resource_usage"
    
    for i in range(10):
        await assistant.process_with_context(f"测试资源使用 {i}", test_session_id)
    
    # 最终内存使用
    final_memory = psutil.Process().memory_info().rss / 1024 / 1024
    print(f"最终内存使用: {final_memory:.2f} MB")
    print(f"内存增长: {final_memory - initial_memory:.2f} MB")
    
    print("✓ 资源使用基准测试完成")
    print()


async def main():
    """运行所有性能基准测试"""
    print("开始性能基准测试...")
    print("=" * 60)
    
    tests = [
        benchmark_context_processing,
        benchmark_memory_operations,
        benchmark_meta_learning,
        benchmark_concurrent_processing,
        benchmark_long_term_coherence,
        benchmark_resource_usage
    ]
    
    for test in tests:
        try:
            await test()
        except Exception as e:
            print("✗ 测试失败:", e)
            print()
    
    print("=" * 60)
    print("性能基准测试完成！")


if __name__ == "__main__":
    asyncio.run(main())
