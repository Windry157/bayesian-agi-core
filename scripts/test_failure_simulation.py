#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模块故障模拟测试
测试系统在各种故障场景下的表现
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.assistant import Assistant


async def test_memory_system_failure():
    """测试记忆系统故障"""
    print("测试 1: 记忆系统故障模拟")
    
    assistant = Assistant()
    test_session_id = "test_memory_failure"
    
    # 模拟记忆系统故障
    original_add = assistant.memory_system.add_memory
    original_retrieve = assistant.memory_system.retrieve_memories
    
    async def mock_failed_add(*args, **kwargs):
        raise Exception("Memory storage failure")
    
    async def mock_failed_retrieve(*args, **kwargs):
        raise Exception("Memory retrieval timeout")
    
    # 注入故障
    assistant.memory_system.add_memory = mock_failed_add
    assistant.memory_system.retrieve_memories = mock_failed_retrieve
    
    try:
        # 处理请求
        result = await assistant.process_with_context(
            "请告诉我关于人工智能的最新进展", 
            test_session_id
        )
        
        # 验证系统能够优雅处理故障
        print("响应:", result.get('response', 'No response')[:100], "...")
        print("✓ 记忆系统故障模拟测试通过")
        
    finally:
        # 恢复原始方法
        assistant.memory_system.add_memory = original_add
        assistant.memory_system.retrieve_memories = original_retrieve
    print()


async def test_context_bridge_failure():
    """测试上下文桥接器故障"""
    print("测试 2: 上下文桥接器故障模拟")
    
    assistant = Assistant()
    test_session_id = "test_context_failure"
    
    # 模拟上下文桥接器故障
    original_load = assistant.context_bridge.load_relevant_context
    original_update = assistant.context_bridge.update_session_context
    
    async def mock_failed_load(*args, **kwargs):
        raise Exception("Context loading failed")
    
    async def mock_failed_update(*args, **kwargs):
        raise Exception("Context update failed")
    
    # 注入故障
    assistant.context_bridge.load_relevant_context = mock_failed_load
    assistant.context_bridge.update_session_context = mock_failed_update
    
    try:
        # 处理请求
        result = await assistant.process_with_context(
            "今天天气怎么样？", 
            test_session_id
        )
        
        # 验证系统能够优雅处理故障
        print("响应:", result.get('response', 'No response')[:100], "...")
        print("✓ 上下文桥接器故障模拟测试通过")
        
    finally:
        # 恢复原始方法
        assistant.context_bridge.load_relevant_context = original_load
        assistant.context_bridge.update_session_context = original_update
    print()


async def test_state_persistence_failure():
    """测试状态持久化故障"""
    print("测试 3: 状态持久化故障模拟")
    
    assistant = Assistant()
    test_session_id = "test_state_failure"
    
    # 模拟状态持久化故障
    original_load = assistant.state_persistence.load_cognitive_state
    original_update = assistant.state_persistence.update_state
    
    async def mock_failed_load():
        raise Exception("State loading failed")
    
    async def mock_failed_update(*args, **kwargs):
        raise Exception("State update failed")
    
    # 注入故障
    assistant.state_persistence.load_cognitive_state = mock_failed_load
    assistant.state_persistence.update_state = mock_failed_update
    
    try:
        # 处理请求
        result = await assistant.process_with_context(
            "你能帮我做什么？", 
            test_session_id
        )
        
        # 验证系统能够优雅处理故障
        print("响应:", result.get('response', 'No response')[:100], "...")
        print("✓ 状态持久化故障模拟测试通过")
        
    finally:
        # 恢复原始方法
        assistant.state_persistence.load_cognitive_state = original_load
        assistant.state_persistence.update_state = original_update
    print()


async def test_meta_learning_failure():
    """测试元学习系统故障"""
    print("测试 4: 元学习系统故障模拟")
    
    assistant = Assistant()
    
    # 模拟元学习系统故障
    original_cycle = assistant.meta_learning.self_improvement_cycle
    
    async def mock_failed_cycle():
        raise Exception("Meta-learning cycle failed")
    
    # 注入故障
    assistant.meta_learning.self_improvement_cycle = mock_failed_cycle
    
    try:
        # 执行自我完善循环
        result = await assistant.self_improvement_cycle()
        
        # 验证系统能够优雅处理故障
        print("结果:", result)
        print("✓ 元学习系统故障模拟测试通过")
        
    finally:
        # 恢复原始方法
        assistant.meta_learning.self_improvement_cycle = original_cycle
    print()


async def test_intrinsic_motivation_failure():
    """测试内在动机系统故障"""
    print("测试 5: 内在动机系统故障模拟")
    
    assistant = Assistant()
    
    # 模拟内在动机系统故障
    original_goals = assistant.intrinsic_motivation.generate_learning_goals
    
    async def mock_failed_goals():
        raise Exception("Goal generation failed")
    
    # 注入故障
    assistant.intrinsic_motivation.generate_learning_goals = mock_failed_goals
    
    try:
        # 生成学习目标
        goals = await assistant.generate_learning_goals()
        
        # 验证系统能够优雅处理故障
        print("生成的目标数量:", len(goals))
        print("✓ 内在动机系统故障模拟测试通过")
        
    finally:
        # 恢复原始方法
        assistant.intrinsic_motivation.generate_learning_goals = original_goals
    print()


async def test_concurrent_failure():
    """测试并发故障场景"""
    print("测试 6: 并发故障模拟")
    
    assistant = Assistant()
    test_session_id = "test_concurrent_failure"
    
    # 模拟多个组件同时故障
    original_memory = assistant.memory_system.retrieve_memories
    original_context = assistant.context_bridge.load_relevant_context
    
    async def mock_failed_memory(*args, **kwargs):
        raise Exception("Memory failure")
    
    async def mock_failed_context(*args, **kwargs):
        raise Exception("Context failure")
    
    # 注入故障
    assistant.memory_system.retrieve_memories = mock_failed_memory
    assistant.context_bridge.load_relevant_context = mock_failed_context
    
    try:
        # 处理请求
        result = await assistant.process_with_context(
            "复杂的多步骤任务测试", 
            test_session_id
        )
        
        # 验证系统能够优雅处理故障
        print("响应:", result.get('response', 'No response')[:100], "...")
        print("✓ 并发故障模拟测试通过")
        
    finally:
        # 恢复原始方法
        assistant.memory_system.retrieve_memories = original_memory
        assistant.context_bridge.load_relevant_context = original_context
    print()


async def test_network_failure_simulation():
    """测试网络故障模拟"""
    print("测试 7: 网络故障模拟")
    
    # 模拟网络延迟
    import time
    original_time = time.sleep
    
    def mock_sleep(seconds):
        # 模拟网络延迟
        time.sleep(seconds * 0.1)  # 减少实际延迟以加速测试
    
    # 注入故障
    time.sleep = mock_sleep
    
    try:
        assistant = Assistant()
        test_session_id = "test_network_failure"
        
        # 处理请求并测量时间
        start_time = time.time()
        result = await assistant.process_with_context(
            "网络故障测试", 
            test_session_id
        )
        end_time = time.time()
        
        # 验证系统能够处理网络延迟
        print("响应:", result.get('response', 'No response')[:100], "...")
        print("处理时间:", end_time - start_time, "秒")
        print("✓ 网络故障模拟测试通过")
        
    finally:
        # 恢复原始方法
        time.sleep = original_time
    print()


async def main():
    """运行所有故障模拟测试"""
    print("开始模块故障模拟测试...")
    print("=" * 60)
    
    tests = [
        test_memory_system_failure,
        test_context_bridge_failure,
        test_state_persistence_failure,
        test_meta_learning_failure,
        test_intrinsic_motivation_failure,
        test_concurrent_failure,
        test_network_failure_simulation
    ]
    
    for test in tests:
        try:
            await test()
        except Exception as e:
            print("✗ 测试失败:", e)
            print()
    
    print("=" * 60)
    print("模块故障模拟测试完成！")


if __name__ == "__main__":
    asyncio.run(main())
