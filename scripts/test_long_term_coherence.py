#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
长期一致性测试框架
测试系统在多轮、多日对话中的上下文保持能力
"""

import asyncio
import sys
import os
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.assistant import Assistant


async def test_multi_day_coherence():
    """测试多日对话一致性"""
    print("测试 1: 多日对话一致性测试")
    
    assistant = Assistant()
    test_session_id = "test_multi_day_coherence"
    
    # 第一天：设置初始约束
    print("\n--- 第一天对话 ---")
    day1_prompts = [
        "我计划下个月去欧洲旅行，预算有限，喜欢历史和美食",
        "推荐一些法国的历史景点",
        "这些景点的大致费用是多少？",
        "有没有便宜的住宿推荐？"
    ]
    
    for i, prompt in enumerate(day1_prompts):
        result = await assistant.process_with_context(prompt, test_session_id)
        print(f"用户: {prompt}")
        print(f"助手: {result.get('response', 'No response')[:100]}...")
        print()
        await asyncio.sleep(0.5)  # 模拟思考时间
    
    # 模拟时间流逝（第二天）
    print("\n--- 第二天对话 ---")
    print("（模拟时间流逝，第二天）")
    await asyncio.sleep(1)
    
    # 第二天：继续对话，测试上下文保持
    day2_prompts = [
        "我们回到昨天的旅行计划",
        "你能帮我制定一个详细的行程吗？",
        "需要考虑我的预算限制",
        "另外，我还想去意大利"
    ]
    
    for i, prompt in enumerate(day2_prompts):
        result = await assistant.process_with_context(prompt, test_session_id)
        print(f"用户: {prompt}")
        print(f"助手: {result.get('response', 'No response')[:100]}...")
        print()
        await asyncio.sleep(0.5)
    
    # 模拟时间流逝（第三天）
    print("\n--- 第三天对话 ---")
    print("（模拟时间流逝，第三天）")
    await asyncio.sleep(1)
    
    # 第三天：测试长期记忆
    day3_prompts = [
        "记得我们之前讨论的欧洲旅行计划吗？",
        "我想调整预算，增加一些",
        "你能重新推荐一些景点吗？",
        "包括法国和意大利的"
    ]
    
    for i, prompt in enumerate(day3_prompts):
        result = await assistant.process_with_context(prompt, test_session_id)
        print(f"用户: {prompt}")
        print(f"助手: {result.get('response', 'No response')[:100]}...")
        print()
        await asyncio.sleep(0.5)
    
    # 验证上下文长度
    context = await assistant.context_bridge.load_relevant_context(test_session_id)
    messages = context.get("session_context", {}).get("messages", [])
    print(f"\n总对话轮数: {len(messages)}")
    print("✓ 多日对话一致性测试完成")
    print()


async def test_complex_task_coherence():
    """测试复杂任务一致性"""
    print("测试 2: 复杂任务一致性测试")
    
    assistant = Assistant()
    test_session_id = "test_complex_task_coherence"
    
    # 复杂任务：计划一个周末科技会议
    print("\n--- 复杂任务：计划科技会议 ---")
    
    task_prompts = [
        "我需要在纽约组织一个为期3天的科技会议，主题是人工智能和机器学习",
        "参会人数约100人，预算5万美元",
        "需要推荐合适的场地",
        "安排3个主题演讲和6个工作坊",
        "邀请5位行业专家作为演讲嘉宾",
        "考虑交通和住宿安排",
        "制定详细的日程安排",
        "如何进行会议推广和注册？"
    ]
    
    for i, prompt in enumerate(task_prompts):
        result = await assistant.process_with_context(prompt, test_session_id)
        print(f"用户: {prompt}")
        print(f"助手: {result.get('response', 'No response')[:100]}...")
        print()
        await asyncio.sleep(0.5)
    
    # 验证系统是否保持了所有约束
    context = await assistant.context_bridge.load_relevant_context(test_session_id)
    global_context = context.get("global_context", {})
    
    # 检查关键信息是否被记住
    key_information = [
        "纽约", "3天", "人工智能", "机器学习",
        "100人", "5万美元", "3个主题演讲",
        "6个工作坊", "5位专家"
    ]
    
    print("\n检查关键信息记忆:")
    for info in key_information:
        found = any(info in key for key in global_context.keys())
        status = "✓" if found else "✗"
        print(f"{status} {info}")
    
    print("\n✓ 复杂任务一致性测试完成")
    print()


async def test_context_switching():
    """测试上下文切换能力"""
    print("测试 3: 上下文切换测试")
    
    assistant = Assistant()
    
    # 创建多个会话
    session1 = "session_work"
    session2 = "session_personal"
    session3 = "session_hobby"
    
    print("\n--- 工作会话 ---")
    work_prompts = [
        "我需要完成一个项目提案",
        "截止日期是下周五",
        "主题是可持续发展"
    ]
    
    for prompt in work_prompts:
        result = await assistant.process_with_context(prompt, session1)
        print(f"用户: {prompt}")
        print(f"助手: {result.get('response', 'No response')[:80]}...")
        print()
        await asyncio.sleep(0.3)
    
    print("\n--- 个人会话 ---")
    personal_prompts = [
        "我想为妻子准备一个生日惊喜",
        "她喜欢花艺和音乐",
        "预算500美元"
    ]
    
    for prompt in personal_prompts:
        result = await assistant.process_with_context(prompt, session2)
        print(f"用户: {prompt}")
        print(f"助手: {result.get('response', 'No response')[:80]}...")
        print()
        await asyncio.sleep(0.3)
    
    print("\n--- 爱好会话 ---")
    hobby_prompts = [
        "我想开始学习摄影",
        "预算1000美元",
        "推荐一些入门相机"
    ]
    
    for prompt in hobby_prompts:
        result = await assistant.process_with_context(prompt, session3)
        print(f"用户: {prompt}")
        print(f"助手: {result.get('response', 'No response')[:80]}...")
        print()
        await asyncio.sleep(0.3)
    
    # 回到工作会话，测试上下文恢复
    print("\n--- 回到工作会话 ---")
    follow_up = "关于可持续发展项目，你有什么具体建议？"
    result = await assistant.process_with_context(follow_up, session1)
    print(f"用户: {follow_up}")
    print(f"助手: {result.get('response', 'No response')[:100]}...")
    print()
    
    # 检查会话数量
    session_count = len(assistant.context_bridge.get_session_contexts())
    print(f"\n活跃会话数量: {session_count}")
    print("✓ 上下文切换测试完成")
    print()


async def test_memory_retention():
    """测试记忆保留能力"""
    print("测试 4: 记忆保留测试")
    
    assistant = Assistant()
    test_session_id = "test_memory_retention"
    
    # 输入一系列信息
    info_prompts = [
        "我的名字是John",
        "我住在纽约",
        "我是一名软件工程师",
        "我喜欢徒步和摄影",
        "我的生日是10月15日"
    ]
    
    print("\n--- 输入个人信息 ---")
    for prompt in info_prompts:
        result = await assistant.process_with_context(prompt, test_session_id)
        print(f"用户: {prompt}")
        print(f"助手: {result.get('response', 'No response')[:80]}...")
        print()
        await asyncio.sleep(0.3)
    
    # 测试记忆检索
    print("\n--- 测试记忆检索 ---")
    test_prompts = [
        "你知道我叫什么名字吗？",
        "我住在哪里？",
        "我的职业是什么？",
        "我有什么爱好？",
        "我的生日是什么时候？"
    ]
    
    correct_count = 0
    for prompt in test_prompts:
        result = await assistant.process_with_context(prompt, test_session_id)
        response = result.get('response', '')
        print(f"用户: {prompt}")
        print(f"助手: {response[:100]}...")
        
        # 简单的答案验证
        if "John" in response and "名字" in prompt:
            correct_count += 1
        elif "纽约" in response and "住" in prompt:
            correct_count += 1
        elif "软件工程师" in response and "职业" in prompt:
            correct_count += 1
        elif ("徒步" in response or "摄影" in response) and "爱好" in prompt:
            correct_count += 1
        elif "10月15日" in response and "生日" in prompt:
            correct_count += 1
        
        print()
        await asyncio.sleep(0.3)
    
    print(f"\n记忆准确率: {correct_count}/{len(test_prompts)}")
    print("✓ 记忆保留测试完成")
    print()


async def test_complex_question_answering():
    """测试复杂问答能力"""
    print("测试 5: 复杂问答一致性测试")
    
    assistant = Assistant()
    test_session_id = "test_complex_qa"
    
    # 提供背景信息
    print("\n--- 提供背景信息 ---")
    background = ""
    background += "公司X是一家科技初创公司，成立于2020年，总部位于旧金山。\n"
    background += "公司的主要产品是AI驱动的客户服务系统。\n"
    background += "创始人是Alice Smith和Bob Johnson。\n"
    background += "公司在2021年获得了A轮融资1000万美元。\n"
    background += "2022年推出了产品的2.0版本。\n"
    background += "2023年公司员工达到100人。\n"
    background += "公司的愿景是通过AI技术改善客户服务体验。"
    
    result = await assistant.process_with_context(background, test_session_id)
    print("用户: [提供公司背景信息]")
    print(f"助手: {result.get('response', 'No response')[:80]}...")
    print()
    
    # 测试复杂问题
    print("\n--- 测试复杂问题 ---")
    questions = [
        "公司X成立于哪一年？",
        "创始人是谁？",
        "公司的主要产品是什么？",
        "什么时候获得了A轮融资？金额是多少？",
        "2022年公司做了什么？",
        "公司的愿景是什么？"
    ]
    
    correct_count = 0
    for question in questions:
        result = await assistant.process_with_context(question, test_session_id)
        response = result.get('response', '')
        print(f"用户: {question}")
        print(f"助手: {response[:100]}...")
        
        # 简单的答案验证
        if "2020" in response and "成立" in question:
            correct_count += 1
        elif ("Alice" in response or "Bob" in response) and "创始人" in question:
            correct_count += 1
        elif "AI" in response and "产品" in question:
            correct_count += 1
        elif "2021" in response and "融资" in question:
            correct_count += 1
        elif "2.0" in response and "2022" in question:
            correct_count += 1
        elif "愿景" in response and "愿景" in question:
            correct_count += 1
        
        print()
        await asyncio.sleep(0.3)
    
    print(f"\n问答准确率: {correct_count}/{len(questions)}")
    print("✓ 复杂问答一致性测试完成")
    print()


async def main():
    """运行所有长期一致性测试"""
    print("开始长期一致性测试...")
    print("=" * 60)
    
    tests = [
        test_multi_day_coherence,
        test_complex_task_coherence,
        test_context_switching,
        test_memory_retention,
        test_complex_question_answering
    ]
    
    for test in tests:
        try:
            await test()
        except Exception as e:
            print("✗ 测试失败:", e)
            print()
    
    print("=" * 60)
    print("长期一致性测试完成！")


if __name__ == "__main__":
    asyncio.run(main())
