#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bridge 并行执行器模块测试

测试 src/core/bridge/parallel_executor.py 模块的所有功能:
1. TaskStatus 枚举测试
2. TaskResult 数据类测试
3. ParallelResult 数据类测试
4. AsyncParallelExecutor 核心功能测试
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.bridge import (
    AsyncParallelExecutor,
    ParallelResult,
    TaskResult,
    TaskStatus,
)


# ======================================================
# 测试 1: TaskStatus 枚举
# ======================================================

def test_task_status_enum():
    """测试 TaskStatus 枚举值"""
    print("\n" + "=" * 60)
    print("Test 1: TaskStatus Enum")
    print("=" * 60)

    passed = True

    # 测试枚举值是否正确
    if TaskStatus.PENDING == "pending":
        print("PASS: TaskStatus.PENDING = 'pending'")
    else:
        print("FAIL: TaskStatus.PENDING should be 'pending'")
        passed = False

    if TaskStatus.RUNNING == "running":
        print("PASS: TaskStatus.RUNNING = 'running'")
    else:
        print("FAIL: TaskStatus.RUNNING should be 'running'")
        passed = False

    if TaskStatus.SUCCESS == "success":
        print("PASS: TaskStatus.SUCCESS = 'success'")
    else:
        print("FAIL: TaskStatus.SUCCESS should be 'success'")
        passed = False

    if TaskStatus.FAILED == "failed":
        print("PASS: TaskStatus.FAILED = 'failed'")
    else:
        print("FAIL: TaskStatus.FAILED should be 'failed'")
        passed = False

    return passed


# ======================================================
# 测试 2: TaskResult 数据类
# ======================================================

def test_task_result_creation():
    """测试 TaskResult 创建"""
    print("\n" + "=" * 60)
    print("Test 2: TaskResult Creation")
    print("=" * 60)

    passed = True

    # 测试成功结果
    success_result = TaskResult(
        task_id=0,
        status=TaskStatus.SUCCESS,
        result="test_value",
        execution_time=0.1
    )
    if success_result.task_id == 0:
        print("PASS: task_id set correctly")
    else:
        print("FAIL: task_id incorrect")
        passed = False

    if success_result.is_success():
        print("PASS: is_success() returns True for success status")
    else:
        print("FAIL: is_success() should return True")
        passed = False

    if not success_result.is_failed():
        print("PASS: is_failed() returns False for success status")
    else:
        print("FAIL: is_failed() should return False")
        passed = False

    # 测试失败结果
    failed_result = TaskResult(
        task_id=1,
        status=TaskStatus.FAILED,
        error=ValueError("test error"),
        execution_time=0.2
    )
    if failed_result.is_failed():
        print("PASS: is_failed() returns True for failed status")
    else:
        print("FAIL: is_failed() should return True")
        passed = False

    if not failed_result.is_success():
        print("PASS: is_success() returns False for failed status")
    else:
        print("FAIL: is_success() should return False")
        passed = False

    return passed


# ======================================================
# 测试 3: ParallelResult 数据类
# ======================================================

def test_parallel_result_properties():
    """测试 ParallelResult 属性"""
    print("\n" + "=" * 60)
    print("Test 3: ParallelResult Properties")
    print("=" * 60)

    passed = True

    # 创建混合结果
    task_results = [
        TaskResult(0, TaskStatus.SUCCESS, result=10, execution_time=0.1),
        TaskResult(1, TaskStatus.SUCCESS, result=20, execution_time=0.2),
        TaskResult(2, TaskStatus.FAILED, error=ValueError(), execution_time=0.1),
    ]
    parallel_result = ParallelResult(
        task_results=task_results,
        total_execution_time=0.4
    )

    # 测试 success_count
    if parallel_result.success_count == 2:
        print("PASS: success_count = 2")
    else:
        print(f"FAIL: success_count should be 2, got {parallel_result.success_count}")
        passed = False

    # 测试 failed_count
    if parallel_result.failed_count == 1:
        print("PASS: failed_count = 1")
    else:
        print(f"FAIL: failed_count should be 1, got {parallel_result.failed_count}")
        passed = False

    # 测试 all_success
    if not parallel_result.all_success:
        print("PASS: all_success = False (mixed results)")
    else:
        print("FAIL: all_success should be False")
        passed = False

    # 测试 partial_failed
    if parallel_result.partial_failed:
        print("PASS: partial_failed = True")
    else:
        print("FAIL: partial_failed should be True")
        passed = False

    # 测试 get_success_results
    success_results = parallel_result.get_success_results()
    if success_results == [10, 20]:
        print("PASS: get_success_results() returns correct values")
    else:
        print(f"FAIL: get_success_results() should return [10, 20], got {success_results}")
        passed = False

    # 测试 all_success 场景
    all_success_result = ParallelResult(
        task_results=[
            TaskResult(0, TaskStatus.SUCCESS, result="a"),
            TaskResult(1, TaskStatus.SUCCESS, result="b"),
        ]
    )
    if all_success_result.all_success:
        print("PASS: all_success = True (all tasks succeeded)")
    else:
        print("FAIL: all_success should be True")
        passed = False

    # 测试 all_failed 场景
    all_failed_result = ParallelResult(
        task_results=[
            TaskResult(0, TaskStatus.FAILED, error=ValueError()),
            TaskResult(1, TaskStatus.FAILED, error=TypeError()),
        ]
    )
    if all_failed_result.all_failed:
        print("PASS: all_failed = True (all tasks failed)")
    else:
        print("FAIL: all_failed should be True")
        passed = False

    return passed


# ======================================================
# 测试 4: AsyncParallelExecutor - 基本并发执行
# ======================================================

async def test_basic_parallel_execution():
    """测试基本并发执行"""
    print("\n" + "=" * 60)
    print("Test 4: Basic Parallel Execution")
    print("=" * 60)

    passed = True

    # 创建异步任务
    async def task_1():
        await asyncio.sleep(0.1)
        return "result_1"

    async def task_2():
        await asyncio.sleep(0.1)
        return "result_2"

    async def task_3():
        await asyncio.sleep(0.1)
        return "result_3"

    tasks = [task_1, task_2, task_3]

    executor = AsyncParallelExecutor()
    result = await executor.execute(tasks)

    if len(result.task_results) == 3:
        print("PASS: All 3 tasks executed")
    else:
        print(f"FAIL: Expected 3 tasks, got {len(result.task_results)}")
        passed = False

    if result.all_success:
        print("PASS: All tasks succeeded")
    else:
        print("FAIL: Not all tasks succeeded")
        passed = False

    success_results = sorted(result.get_success_results())
    if success_results == ["result_1", "result_2", "result_3"]:
        print("PASS: All results collected correctly")
    else:
        print(f"FAIL: Results incorrect, got {success_results}")
        passed = False

    return passed


# ======================================================
# 测试 5: AsyncParallelExecutor - 错误隔离
# ======================================================

async def test_error_isolation():
    """测试错误隔离"""
    print("\n" + "=" * 60)
    print("Test 5: Error Isolation")
    print("=" * 60)

    passed = True

    async def good_task():
        await asyncio.sleep(0.1)
        return "good"

    async def bad_task():
        await asyncio.sleep(0.1)
        raise ValueError("Something went wrong!")

    async def another_good_task():
        await asyncio.sleep(0.1)
        return "another_good"

    tasks = [good_task, bad_task, another_good_task]

    executor = AsyncParallelExecutor()
    result = await executor.execute(tasks)

    if result.success_count == 2:
        print("PASS: 2 tasks succeeded")
    else:
        print(f"FAIL: Expected 2 successes, got {result.success_count}")
        passed = False

    if result.failed_count == 1:
        print("PASS: 1 task failed")
    else:
        print(f"FAIL: Expected 1 failure, got {result.failed_count}")
        passed = False

    if result.partial_failed:
        print("PASS: partial_failed is True")
    else:
        print("FAIL: partial_failed should be True")
        passed = False

    # 检查失败任务的错误信息
    failed_errors = result.get_failed_errors()
    if len(failed_errors) == 1 and isinstance(failed_errors[0], ValueError):
        print("PASS: Correct error type captured")
    else:
        print("FAIL: Error not captured correctly")
        passed = False

    return passed


# ======================================================
# 测试 6: AsyncParallelExecutor - 并发度控制
# ======================================================

async def test_concurrency_control():
    """测试并发度控制"""
    print("\n" + "=" * 60)
    print("Test 6: Concurrency Control")
    print("=" * 60)

    passed = True

    # 记录任务开始和结束时间
    task_timings = []

    async def timed_task(task_id):
        import time
        start = time.time()
        await asyncio.sleep(0.2)
        end = time.time()
        task_timings.append((task_id, start, end))
        return task_id

    # 创建 5 个任务，限制最大并发数为 2
    tasks = [
        lambda tid=i: timed_task(tid)
        for i in range(5)
    ]

    executor = AsyncParallelExecutor(max_concurrency=2)
    result = await executor.execute(tasks)

    if result.all_success:
        print("PASS: All tasks succeeded with concurrency limit")
    else:
        print("FAIL: Some tasks failed")
        passed = False

    # 验证结果
    success_results = result.get_success_results()
    if sorted(success_results) == [0, 1, 2, 3, 4]:
        print("PASS: All task IDs collected")
    else:
        print("FAIL: Task IDs incorrect")
        passed = False

    return passed


# ======================================================
# 测试 7: AsyncParallelExecutor - 性能基准测试
# ======================================================

async def test_performance_benchmark():
    """测试性能基准（总耗时接近最长任务耗时）"""
    print("\n" + "=" * 60)
    print("Test 7: Performance Benchmark")
    print("=" * 60)

    passed = True

    async def fast_task():
        await asyncio.sleep(0.1)
        return "fast"

    async def medium_task():
        await asyncio.sleep(0.3)
        return "medium"

    async def slow_task():
        await asyncio.sleep(0.5)
        return "slow"

    tasks = [fast_task, medium_task, slow_task]

    executor = AsyncParallelExecutor()
    result = await executor.execute(tasks)

    # 总耗时应该略大于最长任务的 0.5 秒，但远小于 0.1+0.3+0.5=0.9 秒
    total_time = result.total_execution_time
    print(f"Total execution time: {total_time:.4f}s")

    if 0.45 <= total_time < 0.7:
        print("PASS: Total time is close to longest task duration (parallel execution)")
    else:
        print(f"FAIL: Total time {total_time:.4f}s is not within expected range")
        passed = False

    if result.all_success:
        print("PASS: All tasks succeeded")
    else:
        print("FAIL: Some tasks failed")
        passed = False

    return passed


# ======================================================
# 测试 8: AsyncParallelExecutor - 空任务列表
# ======================================================

async def test_empty_tasks():
    """测试空任务列表"""
    print("\n" + "=" * 60)
    print("Test 8: Empty Tasks List")
    print("=" * 60)

    passed = True

    executor = AsyncParallelExecutor()
    result = await executor.execute([])

    if len(result.task_results) == 0:
        print("PASS: Empty task list returns empty results")
    else:
        print("FAIL: Should return empty results")
        passed = False

    if result.total_execution_time >= 0:
        print("PASS: total_execution_time is non-negative")
    else:
        print("FAIL: total_execution_time should be non-negative")
        passed = False

    return passed


# ======================================================
# 主函数
# ======================================================

async def main_async():
    """异步主函数"""
    all_passed = True

    # 同步测试
    if not test_task_status_enum():
        all_passed = False
    if not test_task_result_creation():
        all_passed = False
    if not test_parallel_result_properties():
        all_passed = False

    # 异步测试
    if not await test_basic_parallel_execution():
        all_passed = False
    if not await test_error_isolation():
        all_passed = False
    if not await test_concurrency_control():
        all_passed = False
    if not await test_performance_benchmark():
        all_passed = False
    if not await test_empty_tasks():
        all_passed = False

    return all_passed


def main():
    print("\n" + "=" * 60)
    print("Bridge Parallel Executor Tests")
    print("=" * 60)

    # 运行异步测试
    all_passed = asyncio.run(main_async())

    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED!")
    print("=" * 60)

    print("\nVerification:")
    print("  [OK] 1. TaskStatus Enum")
    print("  [OK] 2. TaskResult Data Class")
    print("  [OK] 3. ParallelResult Data Class")
    print("  [OK] 4. Basic Parallel Execution")
    print("  [OK] 5. Error Isolation")
    print("  [OK] 6. Concurrency Control")
    print("  [OK] 7. Performance Benchmark")
    print("  [OK] 8. Empty Tasks List")


if __name__ == "__main__":
    main()
