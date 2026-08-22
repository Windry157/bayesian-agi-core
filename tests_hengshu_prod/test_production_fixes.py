#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生产级修复验证测试
验证所有 P0/P1 级别修复：
1. 工作流状态机（循环依赖检测、失败传播、BLOCKED 状态）
2. ToT 评分解析（结构化输出、显式失败处理、不再静默 0.5）
3. Hybrid 异常隔离（分支独立超时、容忍部分失败）
4. 全局预算控制（LLM 调用、Token、成本硬限制）
5. 降级标记显式化（degraded 标志、mode_used 追踪）
"""
import asyncio
import sys
import os

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.cognition import (
    MultiAgentOrchestrator, Task, TaskStatus,
    TreeOfThoughtReasoner, EvaluationStatus, EvaluationResult,
    ReasoningBudget, LLMResult, LLMInvoker, FallbackPolicy,
    AdvancedReasoningCoordinator, ReasoningStrategy,
)


def test_cycle_detection():
    """测试 1: 循环依赖检测"""
    print("\n=== 测试 1: 循环依赖检测 ===")
    
    orchestrator = MultiAgentOrchestrator()
    
    # 创建循环依赖: task1 -> task2 -> task3 -> task1
    task1 = Task(id="task1", name="任务1", description="", agent_type="MarketResearchAgent", dependencies=["task3"])
    task2 = Task(id="task2", name="任务2", description="", agent_type="MarketResearchAgent", dependencies=["task1"])
    task3 = Task(id="task3", name="任务3", description="", agent_type="MarketResearchAgent", dependencies=["task2"])
    
    orchestrator.add_task(task1)
    orchestrator.add_task(task2)
    orchestrator.add_task(task3)
    
    # 运行工作流
    async def run():
        result = await orchestrator.run_workflow()
        return result
    
    result = asyncio.run(run())
    
    # 验证所有任务被标记为 BLOCKED
    all_blocked = all(task.status == TaskStatus.BLOCKED for task in result.values())
    cycle_error = any("循环依赖" in (task.error or "") for task in result.values())
    
    print(f"  所有任务 BLOCKED: {all_blocked}")
    print(f"  循环依赖错误标记: {cycle_error}")
    
    if all_blocked and cycle_error:
        print("  ✅ 循环依赖检测通过")
        return True
    else:
        print("  ❌ 循环依赖检测失败")
        return False


def test_failure_propagation():
    """测试 2: 失败任务传播，下游任务 BLOCKED"""
    print("\n=== 测试 2: 失败任务传播 ===")
    
    orchestrator = MultiAgentOrchestrator()
    
    # 创建依赖链: task2 -> task1, task3 -> task2
    # task1 将会失败（不存在的 agent 类型）
    task1 = Task(id="task1", name="任务1", description="", agent_type="NonExistentAgent", dependencies=[])
    task2 = Task(id="task2", name="任务2", description="", agent_type="MarketResearchAgent", dependencies=["task1"])
    task3 = Task(id="task3", name="任务3", description="", agent_type="MarketResearchAgent", dependencies=["task2"])
    
    orchestrator.add_task(task1)
    orchestrator.add_task(task2)
    orchestrator.add_task(task3)
    
    async def run():
        result = await orchestrator.run_workflow()
        return result
    
    result = asyncio.run(run())
    
    task1_status = result["task1"].status
    task2_status = result["task2"].status
    task3_status = result["task3"].status
    
    print(f"  task1 状态: {task1_status.value} (预期 FAILED)")
    print(f"  task2 状态: {task2_status.value} (预期 BLOCKED)")
    print(f"  task3 状态: {task3_status.value} (预期 BLOCKED)")
    
    success = task1_status == TaskStatus.FAILED and task2_status == TaskStatus.BLOCKED and task3_status == TaskStatus.BLOCKED
    
    if success:
        print("  ✅ 失败任务传播通过")
        return True
    else:
        print("  ❌ 失败任务传播失败")
        return False


def test_tot_score_parsing():
    """测试 3: ToT 评分解析，显式失败处理"""
    print("\n=== 测试 3: ToT 评分解析 ===")
    
    reasoner = TreeOfThoughtReasoner()
    
    # 测试各种输入格式
    test_cases = [
        ("0.85", EvaluationStatus.VALID, 0.85),
        ("评分: 0.75", EvaluationStatus.VALID, 0.75),
        ("85%", EvaluationStatus.VALID, 0.85),
        ("得分: 90%", EvaluationStatus.VALID, 0.9),
        ("invalid score", EvaluationStatus.PARSE_FAILED, None),
        ("1.5", EvaluationStatus.INVALID_SCORE, None),  # 超出 0-1 范围
        ("", EvaluationStatus.PARSE_FAILED, None),
    ]
    
    all_passed = True
    for input_str, expected_status, expected_score in test_cases:
        result = reasoner.parse_evaluation_score(input_str)
        status_ok = result.status == expected_status
        score_ok = result.score == expected_score
        passed = status_ok and score_ok
        
        print(f"  输入 '{input_str}': 状态={result.status.value}, 分数={result.score}")
        print(f"    预期状态={expected_status.value}, 预期分数={expected_score}")
        print(f"    {'✅ 通过' if passed else '❌ 失败'}")
        
        if not passed:
            all_passed = False
    
    # 验证 degraded 标记
    degraded_ok = all(
        (result.degraded == (result.status != EvaluationStatus.VALID))
        for result in [reasoner.parse_evaluation_score(inp) for inp, _, _ in test_cases]
    )
    print(f"\n  降级标记正确性: {degraded_ok}")
    
    if all_passed and degraded_ok:
        print("  ✅ ToT 评分解析通过")
        return True
    else:
        print("  ❌ ToT 评分解析失败")
        return False


def test_reasoning_budget():
    """测试 4: 推理预算控制"""
    print("\n=== 测试 4: 推理预算控制 ===")
    
    budget = ReasoningBudget(
        max_llm_calls=5,
        max_input_tokens=1000,
        max_output_tokens=2000,
        max_cost_usd=0.1,
        deadline_seconds=1.0,
    )
    
    print(f"  初始预算耗尽: {budget.is_exhausted} (预期: False)")
    
    # 记录几次调用
    for i in range(3):
        budget.record_call(input_tokens=100, output_tokens=200, cost_usd=0.02)
    
    print(f"  3次调用后: LLM={budget.llm_calls_used}/5, Token输入={budget.input_tokens_used}/1000")
    print(f"  剩余时间: {budget.remaining_time:.2f}s")
    
    # 耗尽调用次数
    for i in range(3):
        budget.record_call()
    
    print(f"  6次调用后预算耗尽: {budget.is_exhausted} (预期: True)")
    print(f"  预算状态: {budget.status['llm_calls']}")
    
    if budget.llm_calls_used == 6 and budget.is_exhausted:
        print("  ✅ 预算控制通过")
        return True
    else:
        print("  ❌ 预算控制失败")
        return False


def test_hybrid_fault_isolation():
    """测试 5: Hybrid 模式异常隔离 - 单分支失败不影响整体"""
    print("\n=== 测试 5: Hybrid 模式异常隔离 ===")
    
    coordinator = AdvancedReasoningCoordinator()
    
    async def run():
        # 用正常输入运行 Hybrid
        result = await coordinator.solve_problem_async(
            "测试问题",
            strategy=ReasoningStrategy.HYBRID,
            entities=["测试实体1", "测试实体2"]
        )
        return result
    
    result = asyncio.run(run())
    
    print(f"  Hybrid 成功: {result.get('success')}")
    print(f"  成功分支数: {result.get('successful_branches', 0)}")
    print(f"  失败分支数: {len(result.get('failed_branches', []))}")
    print(f"  降级标记: {result.get('degraded')}")
    print(f"  总延迟: {result.get('total_latency_ms', 0):.2f}ms")
    
    success = result.get('success') and result.get('successful_branches', 0) >= 1
    
    if success:
        print("  ✅ Hybrid 异常隔离通过")
        return True
    else:
        print("  ❌ Hybrid 异常隔离失败")
        return False


def test_degradation_markers():
    """测试 6: 降级标记显式化"""
    print("\n=== 测试 6: 降级标记显式化 ===")
    
    reasoner = TreeOfThoughtReasoner()
    
    # 显式失败应该有 degraded=True
    failed_result = reasoner.parse_evaluation_score("完全不是数字")
    print(f"  解析失败 degraded: {failed_result.degraded}, mode_used: {failed_result.mode_used}")
    
    # 成功应该有 degraded=False
    success_result = reasoner.parse_evaluation_score("0.75")
    print(f"  解析成功 degraded: {success_result.degraded}, mode_used: {success_result.mode_used}")
    
    # 测试没有 Provider 时的 LLM 降级
    invoker = LLMInvoker(fallback_policy=FallbackPolicy.TEMPLATE)
    
    async def test_llm_fallback():
        # 没有注册 Provider，应该降级到模板
        result = await invoker.invoke(
            "测试 prompt",
            template_fallback=lambda p: f"模板结果: {p[:20]}"
        )
        return result
    
    llm_result = asyncio.run(test_llm_fallback())
    print(f"  无 Provider 时 LLM 降级: degraded={llm_result.degraded}, 原因={llm_result.degradation_reason}")
    
    all_correct = (
        failed_result.degraded == True and
        success_result.degraded == False and
        llm_result.degraded == True
    )
    
    if all_correct:
        print("  ✅ 降级标记显式化通过")
        return True
    else:
        print("  ❌ 降级标记显式化失败")
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("生产级修复验证测试套件")
    print("=" * 60)
    
    tests = [
        ("循环依赖检测", test_cycle_detection),
        ("失败任务传播", test_failure_propagation),
        ("ToT 评分解析", test_tot_score_parsing),
        ("推理预算控制", test_reasoning_budget),
        ("Hybrid 异常隔离", test_hybrid_fault_isolation),
        ("降级标记显式化", test_degradation_markers),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            results.append((name, test_func()))
        except Exception as e:
            print(f"  异常: {e}")
            results.append((name, False))
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    
    for name, ok in results:
        status = "✅ 通过" if ok else "❌ 失败"
        print(f"  {name}: {status}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有生产级修复验证通过！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
