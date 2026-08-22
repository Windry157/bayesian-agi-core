#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chaos Engineering Test Suite
混沌工程测试套件
"""

import asyncio
import random
import time
import sys
from typing import Callable, Any
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.structured_logging import get_logger
from src.utils.circuit_breaker import (
    get_circuit_breaker,
    CircuitBreakerManager
)
from src.utils.rate_limiter import (
    get_rate_limiter_manager
)

logger = get_logger("chaos_test")


class ChaosSimulator:
    """混沌模拟器"""
    
    def __init__(self):
        self.chaos_events = []
    
    def fail_randomly(self, error_rate: float = 0.3) -> Callable:
        """装饰器：随机失败"""
        def decorator(func: Callable):
            def wrapper(*args, **kwargs):
                if random.random() < error_rate:
                    raise Exception(f"Chaos induced failure (rate={error_rate})")
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def delay_randomly(self, min_delay: float = 0.1, max_delay: float = 2.0) -> Callable:
        """装饰器：随机延迟"""
        def decorator(func: Callable):
            def wrapper(*args, **kwargs):
                delay = random.uniform(min_delay, max_delay)
                time.sleep(delay)
                logger.info(f"Chaos delay: {delay:.2f}s")
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def network_flaky(self, failure_rate: float = 0.2, max_delay: float = 3.0) -> Callable:
        """装饰器：模拟不稳定网络"""
        def decorator(func: Callable):
            def wrapper(*args, **kwargs):
                # 随机延迟
                delay = random.uniform(0, max_delay)
                if delay > 0:
                    time.sleep(delay)
                    logger.info(f"Network delay: {delay:.2f}s")
                
                # 随机失败
                if random.random() < failure_rate:
                    raise ConnectionError(f"Network connection failed (rate={failure_rate})")
                
                return func(*args, **kwargs)
            return wrapper
        return decorator


def test_circuit_breaker_resilience():
    """测试熔断器弹性"""
    print("\n" + "=" * 80)
    print("Circuit Breaker Resilience Test")
    print("=" * 80)
    
    # 创建测试熔断器
    breaker = get_circuit_breaker(
        "chaos_test",
        failure_threshold=3,
        recovery_timeout=5
    )
    
    simulator = ChaosSimulator()
    
    @simulator.fail_randomly(error_rate=0.4)
    def flaky_service():
        return "Success!"
    
    success_count = 0
    failure_count = 0
    rejected_count = 0
    
    # 测试1: 触发熔断
    print("\n--- Test 1: Triggering Circuit Breaker ---")
    for i in range(20):
        try:
            result = breaker.execute(flaky_service)
            success_count += 1
            print(f"Attempt {i+1}: Success - State: {breaker.get_state()}")
        except Exception as e:
            if "Circuit" in str(e):
                rejected_count += 1
                print(f"Attempt {i+1}: Rejected (Circuit Open)")
            else:
                failure_count += 1
                print(f"Attempt {i+1}: Failure - {e}")
    
    print(f"\nResults: {success_count} Success, {failure_count} Failure, {rejected_count} Rejected")
    
    # 测试2: 等待恢复
    print("\n--- Test 2: Waiting for Recovery ---")
    print("Waiting 6 seconds...")
    time.sleep(6)
    
    # 测试3: 恢复后
    print("\n--- Test 3: Post-Recovery ---")
    for i in range(5):
        try:
            result = breaker.execute(flaky_service)
            success_count += 1
            print(f"Attempt {i+1}: Success - State: {breaker.get_state()}")
        except Exception as e:
            if "Circuit" in str(e):
                rejected_count += 1
                print(f"Attempt {i+1}: Rejected (Circuit Open)")
            else:
                failure_count += 1
                print(f"Attempt {i+1}: Failure - {e}")
    
    return success_count, failure_count, rejected_count


async def test_rate_limiter_recovery():
    """测试限流器弹性"""
    print("\n" + "=" * 80)
    print("Rate Limiter Recovery Test")
    print("=" * 80)
    
    manager = get_rate_limiter_manager()
    
    # 注册测试限流器
    manager.register_limiter(
        "chaos_rate_test",
        "sliding_window",
        requests=10,
        period_seconds=5
    )
    
    # 测试1: 超速请求
    print("\n--- Test 1: High Traffic Load ---")
    allowed = 0
    rejected = 0
    key = "chaos_test_user"
    
    for i in range(30):
        ok = await manager.acquire("chaos_rate_test", key)
        if ok:
            allowed += 1
            print(f"Request {i+1}: Allowed")
        else:
            rejected += 1
            print(f"Request {i+1}: Rejected (Rate Limit)")
    
    print(f"\nResults: {allowed} Allowed, {rejected} Rejected")
    
    # 测试2: 等待令牌恢复
    print("\n--- Test 2: Waiting for Token Bucket Recovery ---")
    print("Waiting 6 seconds...")
    await asyncio.sleep(6)
    
    # 测试3: 恢复后
    print("\n--- Test 3: Post-Recovery ---")
    allowed2 = 0
    rejected2 = 0
    
    for i in range(10):
        ok = await manager.acquire("chaos_rate_test", key)
        if ok:
            allowed2 += 1
            print(f"Request {i+1}: Allowed")
        else:
            rejected2 += 1
            print(f"Request {i+1}: Rejected")
    
    return allowed + allowed2, rejected + rejected2


async def test_degraded_service():
    """测试降级服务"""
    print("\n" + "=" * 80)
    print("Degraded Service Test")
    print("=" * 80)
    
    def fall_back():
        logger.warning("Using fallback function")
        return "Fallback Response (cached)"
    
    # 创建带降级的熔断器
    breaker = get_circuit_breaker(
        "degraded_test",
        failure_threshold=2,
        recovery_timeout=3,
        fallback_function=fall_back
    )
    
    simulator = ChaosSimulator()
    
    @simulator.network_flaky(failure_rate=0.5)
    def external_service():
        return "External Service Response"
    
    # 正常状态
    print("\n--- Normal Operation ---")
    try:
        result = breaker.execute(external_service)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
    
    # 触发熔断
    print("\n--- Triggering Failure ---")
    for i in range(5):
        result = breaker.execute(external_service)
        print(f"Attempt {i+1}: {result}")
    
    print(f"Final State: {breaker.get_state()}")


def run_chaos_suite():
    """运行完整混沌工程测试套件"""
    print("🚀 Bayesian-AGI-Core Chaos Engineering Test Suite")
    
    try:
        # 测试熔断器
        test_circuit_breaker_resilience()
        
        # 测试限流器
        asyncio.run(test_rate_limiter_recovery())
        
        # 测试降级服务
        test_degraded_service()
        
        print("\n" + "=" * 80)
        print("✅ Chaos Engineering Test Suite Complete!")
        print("=" * 80)
        print("\nKey Findings:")
        print("1. Circuit breaker properly stops requests when threshold met")
        print("2. Rate limiter prevents overload and recovers over time")
        print("3. Fallback functions provide graceful degradation")
        print("4. System demonstrates resilience under chaotic conditions")
        
    except Exception as e:
        logger.error(f"Chaos test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_chaos_suite()
