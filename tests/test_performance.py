#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import time
import random
from pathlib import Path
from datetime import datetime
from statistics import mean, median
from typing import List, Dict, Any, Callable

sys.path.insert(0, str(Path(__file__).parent.parent))


class PerformanceTester:
    """性能测试基类"""

    def __init__(self, name: str):
        self.name = name
        self.results = []

    def run(self, func: Callable, iterations: int = 1000, warmup: int = 100) -> Dict[str, Any]:
        for _ in range(warmup):
            func()

        timings = []
        for _ in range(iterations):
            start = time.perf_counter()
            func()
            duration = (time.perf_counter() - start) * 1000
            timings.append(duration)

        result = {
            "test_name": self.name,
            "iterations": iterations,
            "avg_ms": mean(timings),
            "median_ms": median(timings),
            "min_ms": min(timings),
            "max_ms": max(timings),
            "p50_ms": sorted(timings)[int(iterations * 0.5)],
            "p95_ms": sorted(timings)[int(iterations * 0.95)],
            "p99_ms": sorted(timings)[int(iterations * 0.99)],
            "throughput": iterations / sum(timings) * 1000,
        }
        self.results.append(result)
        return result

    def print_summary(self):
        print(f"\n{'='*60}")
        print(f"性能测试结果: {self.name}")
        print(f"{'='*60}")
        for r in self.results:
            print(f"\n测试: {r['test_name']}")
            print(f"  迭代次数: {r['iterations']}")
            print(f"  平均延迟: {r['avg_ms']:.3f}ms")
            print(f"  P50: {r['p50_ms']:.3f}ms")
            print(f"  P95: {r['p95_ms']:.3f}ms")
            print(f"  P99: {r['p99_ms']:.3f}ms")
            print(f"  吞吐量: {r['throughput']:.0f} ops/sec")


def test_saga_orchestrator():
    print("\n" + "="*60)
    print("Saga 编排器性能测试")
    print("="*60)

    from src.core.distributed.saga_orchestrator import SagaOrchestrator

    tester = PerformanceTester("Saga 创建事务")

    def create_tx():
        orchestrator = SagaOrchestrator()
        orchestrator.create_transaction("test")

    tester.run(create_tx, iterations=1000)

    tester = PerformanceTester("Saga 执行简单事务")
    orchestrator = SagaOrchestrator()

    def simple_step():
        return True

    def execute_simple_saga():
        tx_id = orchestrator.create_transaction("simple")
        orchestrator.add_step(tx_id, "step1", simple_step, None)
        orchestrator.execute(tx_id)

    tester.run(execute_simple_saga, iterations=500)

    tester = PerformanceTester("Saga 执行多步骤事务")
    orchestrator = SagaOrchestrator()

    def step1():
        return True

    def step2():
        return True

    def step3():
        return True

    def execute_multi_step():
        tx_id = orchestrator.create_transaction("multi")
        orchestrator.add_step(tx_id, "step1", step1, None)
        orchestrator.add_step(tx_id, "step2", step2, None)
        orchestrator.add_step(tx_id, "step3", step3, None)
        orchestrator.execute(tx_id)

    tester.run(execute_multi_step, iterations=200)

    tester.print_summary()


def test_event_bus():
    print("\n" + "="*60)
    print("事件总线性能测试")
    print("="*60)

    from src.core.distributed.event_bus import EventBus, DomainEvent, EventType

    tester = PerformanceTester("EventBus 发布事件")
    bus = EventBus()

    def publish_event():
        event = DomainEvent.create(
            event_type=EventType.CUSTOM,
            aggregate_id="perf",
            aggregate_type="test",
            payload={"key": "value"},
            source="perf_test",
        )
        bus.publish(event)

    tester.run(publish_event, iterations=5000)

    tester = PerformanceTester("EventBus 发布事件（带订阅者）")
    bus = EventBus()

    def handler(event):
        pass

    bus.subscribe(handler, event_type=None)

    def publish_with_sub():
        event = DomainEvent.create(
            event_type=EventType.CUSTOM,
            aggregate_id="perf",
            aggregate_type="test",
        )
        bus.publish(event)

    tester.run(publish_with_sub, iterations=5000)

    tester = PerformanceTester("EventBus 多订阅者")
    bus = EventBus()

    for _ in range(10):
        bus.subscribe(handler, event_type=None)

    def publish_multi_topic():
        event = DomainEvent.create(
            event_type=EventType.CUSTOM,
            aggregate_id="perf",
            aggregate_type="test",
        )
        bus.publish(event)

    tester.run(publish_multi_topic, iterations=2000)

    tester.print_summary()


def test_circuit_breaker():
    print("\n" + "="*60)
    print("熔断器性能测试")
    print("="*60)

    from src.core.distributed.enterprise_resilience import CircuitBreaker

    tester = PerformanceTester("CircuitBreaker 正常调用")
    cb = CircuitBreaker(name="perf-cb")

    def success_func():
        return "ok"

    def call_success():
        cb.execute(success_func)

    tester.run(call_success, iterations=10000)

    tester = PerformanceTester("CircuitBreaker 失败调用")
    cb = CircuitBreaker(name="perf-cb-fail")

    def fail_func():
        raise Exception("Failed")

    def call_fail():
        try:
            cb.execute(fail_func)
        except Exception:
            pass

    tester.run(call_fail, iterations=5000)

    tester.print_summary()


def test_memory_compressor():
    print("\n" + "="*60)
    print("记忆压缩器性能测试")
    print("="*60)

    from src.core.memory.memory_compressor import MemoryCompressor

    test_memories = []
    for i in range(1000):
        test_memories.append({
            "id": f"m{i}",
            "content": f"这是一条关于主题 {i % 10} 的记忆内容，用于测试压缩性能",
            "importance": random.random(),
            "created_at": datetime.now().isoformat(),
            "access_count": random.randint(0, 50),
        })

    tester = PerformanceTester("MemoryCompressor 重要性压缩 (1000条)")
    compressor = MemoryCompressor()

    def compress_importance():
        compressor.compress(test_memories, strategy="importance", keep_ratio=0.5)

    tester.run(compress_importance, iterations=50)

    tester = PerformanceTester("MemoryCompressor 相似度压缩 (1000条)")

    def compress_similarity():
        compressor.compress(test_memories, strategy="similarity")

    tester.run(compress_similarity, iterations=20)

    tester.print_summary()


def test_batch_processor():
    print("\n" + "="*60)
    print("批量处理器性能测试")
    print("="*60)

    from src.core.distributed.scalable_messaging import BatchProcessor, BatchConfig

    tester = PerformanceTester("BatchProcessor 小批量添加")

    processed = []

    def process_batch(items):
        processed.extend(items)

    def add_items():
        config = BatchConfig(max_batch_size=10)
        processor = BatchProcessor(process_func=process_batch, config=config)
        for i in range(100):
            processor.add({"id": i})
        processor.flush()

    tester.run(add_items, iterations=500)

    tester = PerformanceTester("BatchProcessor 大批量")

    def add_large_batch():
        config = BatchConfig(max_batch_size=100)
        processor = BatchProcessor(process_func=process_batch, config=config)
        for i in range(1000):
            processor.add({"id": i})
        processor.flush()

    tester.run(add_large_batch, iterations=100)

    tester.print_summary()


def test_token_bucket():
    print("\n" + "="*60)
    print("令牌桶性能测试")
    print("="*60)

    from src.core.distributed.scalable_messaging import TokenBucket, LeakyBucket

    tester = PerformanceTester("TokenBucket 限流检查")
    bucket = TokenBucket(capacity=10000, fill_rate=1000)

    def check_token():
        bucket.acquire()

    tester.run(check_token, iterations=50000)

    tester = PerformanceTester("LeakyBucket 限流检查")
    bucket = LeakyBucket(capacity=10000, leak_rate=1000)

    def check_leak():
        bucket.add()

    tester.run(check_leak, iterations=50000)

    tester.print_summary()


def test_metrics_collector():
    print("\n" + "="*60)
    print("指标收集器性能测试")
    print("="*60)

    from src.core.monitoring.metrics import MetricsCollector

    tester = PerformanceTester("MetricsCollector 记录指标")
    collector = MetricsCollector()

    def record_metric():
        collector.set_gauge("test", random.random(), labels={"tag": "value"})

    tester.run(record_metric, iterations=20000)

    tester = PerformanceTester("MetricsCollector 记录性能")
    collector = MetricsCollector()

    @collector.measure_performance("op")
    def perf_op():
        pass

    def record_perf():
        perf_op()

    tester.run(record_perf, iterations=20000)

    tester = PerformanceTester("MetricsCollector 获取统计")
    collector = MetricsCollector()

    @collector.measure_performance("op")
    def perf_op2():
        pass

    for _ in range(1000):
        perf_op2()

    def get_stats():
        collector.get_statistics()

    tester.run(get_stats, iterations=5000)

    tester.print_summary()


def test_tree_of_thought():
    print("\n" + "="*60)
    print("树状思维推理性能测试")
    print("="*60)

    from src.core.cognition.tree_of_thought import (
        TreeOfThoughtReasoner,
        TreeSearchConfig,
    )

    tester = PerformanceTester("TreeOfThought 小树推理")
    config = TreeSearchConfig(max_depth=2, branch_factor=2)
    reasoner = TreeOfThoughtReasoner(config=config)

    def gen_func(thought):
        return [f"{thought}-{i}" for i in range(2)]

    evaluator = lambda x: random.random()

    def small_reasoning():
        reasoner.reason("test", generator=gen_func, evaluator=evaluator)

    tester.run(small_reasoning, iterations=200)

    tester = PerformanceTester("TreeOfThought 大树推理")
    config = TreeSearchConfig(max_depth=4, branch_factor=3)
    reasoner = TreeOfThoughtReasoner(config=config)

    def gen_func_big(thought):
        return [f"{thought}-{i}" for i in range(3)]

    def big_reasoning():
        reasoner.reason("test", generator=gen_func_big, evaluator=evaluator)

    tester.run(big_reasoning, iterations=50)

    tester.print_summary()


def test_concurrent_events():
    print("\n" + "="*60)
    print("并发场景模拟测试")
    print("="*60)

    from src.core.distributed.event_bus import EventBus, DomainEvent, EventType

    tester = PerformanceTester("混合操作序列")
    bus = EventBus()

    for _ in range(5):
        def h(event):
            pass
        bus.subscribe(h, event_type=None)

    def mixed_ops():
        for _ in range(10):
            event = DomainEvent.create(
                event_type=EventType.CUSTOM,
                aggregate_id="perf",
                aggregate_type="test",
                payload={"data": random.randint(0, 100)},
            )
            bus.publish(event)

    tester.run(mixed_ops, iterations=1000)

    tester.print_summary()


def run_all_performance_tests():
    print("="*60)
    print("Bayesian AGI Core 企业级功能性能测试套件")
    print("="*60)
    print(f"开始时间: {datetime.now()}")

    test_saga_orchestrator()
    test_event_bus()
    test_circuit_breaker()
    test_memory_compressor()
    test_batch_processor()
    test_token_bucket()
    test_metrics_collector()
    test_tree_of_thought()
    test_concurrent_events()

    print("\n" + "="*60)
    print("所有性能测试完成")
    print(f"结束时间: {datetime.now()}")
    print("="*60)


if __name__ == "__main__":
    run_all_performance_tests()
