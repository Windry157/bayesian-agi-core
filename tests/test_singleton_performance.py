#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能基准测试 - Assistant 单例模式

测量 get_instance() 的性能基线，确保在压力下依然高效。
"""

import time
import threading
import statistics
from pathlib import Path
from unittest.mock import MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.assistant_singleton import AssistantSingleton


class PerformanceBenchmark:
    """性能基准测试"""

    def __init__(self):
        self.results = {}

    def benchmark_sequential_access(self, iterations: int = 10000) -> dict:
        """测试顺序访问性能

        Args:
            iterations: 访问次数

        Returns:
            dict: 性能统计
        """
        AssistantSingleton.reset()

        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            AssistantSingleton.get_instance()
            end = time.perf_counter()
            times.append((end - start) * 1000)  # 转换为毫秒

        return self._analyze_times(times, "sequential")

    def benchmark_concurrent_access(
        self, threads: int = 50, iterations_per_thread: int = 1000
    ) -> dict:
        """测试并发访问性能

        Args:
            threads: 线程数
            iterations_per_thread: 每个线程的访问次数

        Returns:
            dict: 性能统计
        """
        AssistantSingleton.reset()
        barrier = threading.Barrier(threads)
        times = []
        lock = threading.Lock()

        def worker():
            nonlocal times
            barrier.wait()  # 同步开始
            local_times = []
            for _ in range(iterations_per_thread):
                start = time.perf_counter()
                AssistantSingleton.get_instance()
                end = time.perf_counter()
                local_times.append((end - start) * 1000)
            with lock:
                times.extend(local_times)

        thread_list = [threading.Thread(target=worker) for _ in range(threads)]
        start_time = time.perf_counter()
        for t in thread_list:
            t.start()
        for t in thread_list:
            t.join()
        total_time = time.perf_counter() - start_time

        result = self._analyze_times(times, "concurrent")
        result["total_time_seconds"] = round(total_time, 3)
        result["total_operations"] = threads * iterations_per_thread
        result["throughput_ops_per_sec"] = round(
            result["total_operations"] / total_time, 0
        )
        return result

    def benchmark_mock_mode(self, iterations: int = 10000) -> dict:
        """测试 Mock 模式性能

        Args:
            iterations: 访问次数

        Returns:
            dict: 性能统计
        """
        AssistantSingleton.reset()
        mock = MagicMock()
        AssistantSingleton.set_mock(mock)

        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            AssistantSingleton.get_instance()
            end = time.perf_counter()
            times.append((end - start) * 1000)

        AssistantSingleton.use_real_instance()
        result = self._analyze_times(times, "mock_mode")
        return result

    def benchmark_first_call_vs_subsequent(self) -> dict:
        """对比首次调用和后续调用性能

        Returns:
            dict: 性能对比
        """
        AssistantSingleton.reset()

        # 首次调用（需要创建实例）
        start = time.perf_counter()
        AssistantSingleton.get_instance()
        first_call_ms = (time.perf_counter() - start) * 1000

        # 后续调用（直接返回）
        subsequent_times = []
        for _ in range(1000):
            start = time.perf_counter()
            AssistantSingleton.get_instance()
            end = time.perf_counter()
            subsequent_times.append((end - start) * 1000)

        avg_subsequent = statistics.mean(subsequent_times)
        speedup = first_call_ms / avg_subsequent if avg_subsequent > 0 else float("inf")

        return {
            "first_call_ms": round(first_call_ms, 4),
            "subsequent_avg_ms": round(avg_subsequent, 4),
            "subsequent_p50_ms": round(statistics.median(subsequent_times), 4),
            "subsequent_p99_ms": round(
                sorted(subsequent_times)[int(len(subsequent_times) * 0.99)], 4
            ),
            "speedup_factor": round(speedup, 1),
        }

    def _analyze_times(self, times: list, name: str) -> dict:
        """分析时间列表

        Args:
            times: 时间列表（毫秒）
            name: 测试名称

        Returns:
            dict: 统计结果
        """
        sorted_times = sorted(times)
        return {
            "test_name": name,
            "iterations": len(times),
            "min_ms": round(min(times), 4),
            "max_ms": round(max(times), 4),
            "mean_ms": round(statistics.mean(times), 4),
            "median_ms": round(statistics.median(times), 4),
            "p95_ms": round(sorted_times[int(len(sorted_times) * 0.95)], 4),
            "p99_ms": round(sorted_times[int(len(sorted_times) * 0.99)], 4),
            "std_dev_ms": round(statistics.stdev(times), 4) if len(times) > 1 else 0,
        }


def run_performance_tests():
    """运行所有性能测试"""
    benchmark = PerformanceBenchmark()

    print("=" * 80)
    print("性能基准测试 - Assistant 单例模式")
    print("=" * 80)

    # 测试 1: 顺序访问
    print("\n[测试 1/4] 顺序访问 (10,000 次)")
    print("-" * 40)
    result = benchmark.benchmark_sequential_access(10000)
    print(f"  平均延迟: {result['mean_ms']} ms")
    print(f"  P50: {result['median_ms']} ms")
    print(f"  P95: {result['p95_ms']} ms")
    print(f"  P99: {result['p99_ms']} ms")
    print(f"  最大延迟: {result['max_ms']} ms")

    # 测试 2: 首次调用 vs 后续调用
    print("\n[测试 2/4] 首次调用 vs 后续调用")
    print("-" * 40)
    result = benchmark.benchmark_first_call_vs_subsequent()
    print(f"  首次调用: {result['first_call_ms']} ms")
    print(f"  后续平均: {result['subsequent_avg_ms']} ms")
    print(f"  加速倍数: {result['speedup_factor']}x")

    # 测试 3: 并发访问
    print("\n[测试 3/4] 并发访问 (50 线程 x 1,000 次 = 50,000 次)")
    print("-" * 40)
    result = benchmark.benchmark_concurrent_access(50, 1000)
    print(f"  总耗时: {result['total_time_seconds']} s")
    print(f"  吞吐量: {result['throughput_ops_per_sec']} ops/s")
    print(f"  平均延迟: {result['mean_ms']} ms")
    print(f"  P99: {result['p99_ms']} ms")

    # 测试 4: Mock 模式
    print("\n[测试 4/4] Mock 模式性能 (10,000 次)")
    print("-" * 40)
    result = benchmark.benchmark_mock_mode(10000)
    print(f"  平均延迟: {result['mean_ms']} ms")
    print(f"  P99: {result['p99_ms']} ms")

    print("\n" + "=" * 80)
    print("性能基准测试完成!")
    print("=" * 80)

    return benchmark


def assert_performance_requirements():
    """断言性能要求是否满足"""

    benchmark = PerformanceBenchmark()
    errors = []

    # 要求 1: 后续调用平均延迟 < 0.1ms
    result = benchmark.benchmark_first_call_vs_subsequent()
    if result["subsequent_avg_ms"] > 0.1:
        errors.append(
            f"后续调用延迟过高: {result['subsequent_avg_ms']}ms > 0.1ms"
        )

    # 要求 2: 并发 1000 次调用的 P99 < 1ms
    result = benchmark.benchmark_concurrent_access(10, 100)
    if result["p99_ms"] > 1.0:
        errors.append(f"并发 P99 延迟过高: {result['p99_ms']}ms > 1ms")

    # 要求 3: Mock 模式平均延迟 < 0.05ms
    result = benchmark.benchmark_mock_mode(1000)
    if result["mean_ms"] > 0.05:
        errors.append(f"Mock 模式延迟过高: {result['mean_ms']}ms > 0.05ms")

    if errors:
        print("❌ 性能要求未满足:")
        for error in errors:
            print(f"   - {error}")
        return False
    else:
        print("✅ 所有性能要求已满足!")
        return True


if __name__ == "__main__":
    run_performance_tests()
    print()
    assert_performance_requirements()
