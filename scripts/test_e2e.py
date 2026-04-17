#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端测试脚本
测试完整的系统工作流程
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.assistant import Assistant


async def test_full_contextual_loop():
    """测试完整的上下文循环"""
    print("测试 1: 完整上下文循环测试")
    
    assistant = Assistant()
    test_session_id = "test_trip_planning"
    test_prompt = "计划一个周末去西雅图的旅行，重点关注历史景点，并提供预算明细"
    
    # 1. 初始化上下文
    await assistant.context_bridge.update_session_context(test_session_id, {
        "messages": [],
        "metadata": {"topic": "trip planning", "location": "Seattle"}
    })
    
    # 2. 处理请求
    result = await assistant.process_with_context(test_prompt, test_session_id)
    
    # 3. 验证响应
    print("响应:", result.get('response', 'No response')[:100], "...")
    
    # 4. 验证上下文更新
    context = await assistant.context_bridge.load_relevant_context(test_session_id)
    message_count = len(context.get("session_context", {}).get("messages", []))
    print("会话消息数量:", message_count)
    
    # 5. 验证认知状态更新
    cognitive_state = await assistant.state_persistence.load_cognitive_state()
    domains = cognitive_state.get("knowledge", {}).get("domains", [])
    print("知识领域数量:", len(domains))
    
    print("✓ 完整上下文循环测试完成")
    print()


async def test_inter_module_failure_simulation():
    """测试模块间故障模拟"""
    print("测试 2: 模块故障模拟测试")
    
    assistant = Assistant()
    test_session_id = "test_failure_simulation"
    
    # 1. 模拟记忆系统故障
    original_retrieve = assistant.memory_system.retrieve_memories
    
    def mock_failed_retrieve(*args, **kwargs):
        raise Exception("Memory retrieval timeout")
    
    # 2. 注入故障
    assistant.memory_system.retrieve_memories = mock_failed_retrieve
    
    try:
        # 3. 处理请求
        result = await assistant.process_with_context(
            "请告诉我关于人工智能的最新进展", 
            test_session_id
        )
        
        # 4. 验证系统能够优雅处理故障
        print("响应:", result.get('response', 'No response')[:100], "...")
        print("✓ 模块故障模拟测试完成")
        
    finally:
        # 5. 恢复原始方法
        assistant.memory_system.retrieve_memories = original_retrieve
    print()


async def test_long_term_coherence():
    """测试长期一致性"""
    print("测试 3: 长期一致性测试")
    
    assistant = Assistant()
    test_session_id = "test_long_term_coherence"
    
    # 1. 初始请求：设置约束
    initial_prompt = "我计划下个月去日本旅行，预算有限，喜欢历史和美食"
    result1 = await assistant.process_with_context(initial_prompt, test_session_id)
    print("初始响应:", result1.get('response', 'No response')[:100], "...")
    
    # 2. 后续请求：依赖初始约束
    follow_up_prompt = "推荐一些东京的历史景点"
    result2 = await assistant.process_with_context(follow_up_prompt, test_session_id)
    print("后续响应:", result2.get('response', 'No response')[:100], "...")
    
    # 3. 再次测试，确保上下文保持
    second_follow_up = "这些景点的大致费用是多少？"
    result3 = await assistant.process_with_context(second_follow_up, test_session_id)
    print("费用响应:", result3.get('response', 'No response')[:100], "...")
    
    # 4. 验证上下文长度
    context = await assistant.context_bridge.load_relevant_context(test_session_id)
    message_count = len(context.get("session_context", {}).get("messages", []))
    print("总消息数量:", message_count)
    
    print("✓ 长期一致性测试完成")
    print()


async def test_system_health():
    """测试系统健康状态"""
    print("测试 4: 系统健康状态测试")
    
    assistant = Assistant()
    health = assistant.get_system_health()
    
    print("元学习状态:", health.get('meta_learning', {}))
    print("内在动机状态:", health.get('intrinsic_motivation', {}))
    print("认知状态:", health.get('cognitive_state', {}))
    print("上下文桥接器状态:", health.get('context_bridge', {}))
    
    print("✓ 系统健康状态测试完成")
    print()


async def test_self_improvement():
    """测试自我完善循环"""
    print("测试 5: 自我完善循环测试")
    
    assistant = Assistant()
    result = await assistant.self_improvement_cycle()
    
    print("自我完善结果:", result.get('metrics', {}))
    print("✓ 自我完善循环测试完成")
    print()


async def test_learning_goals():
    """测试学习目标生成"""
    print("测试 6: 学习目标生成测试")
    
    assistant = Assistant()
    goals = await assistant.generate_learning_goals()
    
    print("生成的学习目标数量:", len(goals))
    for i, goal in enumerate(goals[:3]):  # 只显示前3个目标
        print("目标", i+1, ":", goal.get('description', 'No description'))
        print("  类型:", goal.get('type', 'No type'))
        print("  优先级:", goal.get('priority', 'No priority'))
    
    print("✓ 学习目标生成测试完成")
    print()


async def main():
    """运行所有测试"""
    print("开始端到端测试...")
    print("=" * 60)
    
    tests = [
        test_full_contextual_loop,
        test_inter_module_failure_simulation,
        test_long_term_coherence,
        test_system_health,
        test_self_improvement,
        test_learning_goals
    ]
    
    for test in tests:
        try:
            await test()
        except Exception as e:
            print(f"✗ 测试失败: {e}")
            print()
    
    print("=" * 60)
    print("端到端测试完成！")


if __name__ == "__main__":
    asyncio.run(main())
