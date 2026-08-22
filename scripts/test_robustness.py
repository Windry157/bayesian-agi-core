#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
健壮性功能测试脚本
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.structured_logging import get_logger, info, warning, error
from src.utils.circuit_breaker import get_circuit_breaker, CircuitBreakerManager
from src.utils.rate_limiter import get_rate_limiter_manager

logger = get_logger("test_robustness")


def test_structured_logging():
    """测试结构化日志"""
    print("\n" + "=" * 60)
    print("测试结构化日志系统")
    print("=" * 60)
    
    info("这是一条信息日志")
    warning("这是一条警告日志")
    error("这是一条错误日志")
    
    print("✅ 结构化日志测试完成")


def test_circuit_breaker():
    """测试熔断器"""
    print("\n" + "=" * 60)
    print("测试熔断器")
    print("=" * 60)
    
    # 创建测试熔断器
    breaker = get_circuit_breaker(
        'test_circuit',
        failure_threshold=3,
        recovery_timeout=2
    )
    
    print(f"初始状态: {breaker.get_state()}")
    
    # 测试正常请求
    def success_func():
        return "success"
    
    result = breaker.execute(success_func)
    print(f"成功请求结果: {result}")
    print(f"当前状态: {breaker.get_state()}")
    
    # 测试失败请求
    def fail_func():
        raise Exception("Test failure")
    
    print("\n触发失败请求...")
    for i in range(3):
        try:
            breaker.execute(fail_func)
        except Exception as e:
            print(f"第 {i+1} 次失败: {e}")
    
    metrics = breaker.get_metrics()
    print(f"失败指标: {metrics}")
    print(f"当前状态: {breaker.get_state()}")
    
    # 测试熔断后的请求
    print("\n尝试在熔断状态下请求...")
    try:
        breaker.execute(success_func)
    except Exception as e:
        print(f"熔断状态下的请求被拒绝: {e}")
    
    print("\n熔断器列表:")
    circuits = CircuitBreakerManager.list_circuits()
    for name, state in circuits.items():
        print(f"  - {name}: {state}")
    
    print("✅ 熔断器测试完成")


async def test_rate_limiter():
    """测试限流器"""
    print("\n" + "=" * 60)
    print("测试限流器")
    print("=" * 60)
    
    manager = get_rate_limiter_manager()
    
    # 注册测试限流器
    manager.register_limiter(
        'test_limiter',
        'sliding_window',
        requests=5,
        period_seconds=5
    )
    
    print(f"限流器列表: {manager.list_limiters()}")
    
    # 测试限流
    key = "test_user"
    allowed_count = 0
    
    print(f"\n尝试发送请求...")
    for i in range(10):
        allowed = await manager.acquire('test_limiter', key)
        if allowed:
            allowed_count += 1
            print(f"  请求 {i+1}: ✅ 允许")
        else:
            print(f"  请求 {i+1}: ❌ 拒绝")
    
    print(f"允许的请求数: {allowed_count}")
    
    # 获取统计信息
    stats = manager.get_stats('test_limiter', key)
    print(f"统计信息: {stats}")
    
    print("✅ 限流器测试完成")


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Bayesian-AGI-Core 健壮性功能测试")
    print("=" * 60)
    
    try:
        test_structured_logging()
        test_circuit_breaker()
        await test_rate_limiter()
        
        print("\n" + "=" * 60)
        print("🎉 所有测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
