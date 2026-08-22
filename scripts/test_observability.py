#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可观测性模块测试脚本
验证链路追踪、指标监控和速率限制功能
"""

import asyncio
import time
import sys
sys.path.insert(0, "e:\\laowut\\Trae CN\\bayesian-agi-core")

from src.core.observability import (
    tracer,
    trace_method,
    metrics_collector,
    monitor_latency,
    print_metrics_summary,
    rate_limiter,
    rate_limit,
    setup_default_rate_limits,
    RateLimitExceededError
)


@trace_method("memory_operation")
@monitor_latency("memory_operation")
async def memory_operation(delay_ms: int):
    """模拟记忆操作"""
    await asyncio.sleep(delay_ms / 1000)
    return {"status": "success", "delay_ms": delay_ms}


@trace_method("vector_query")
@monitor_latency("vector_query")
async def vector_query(delay_ms: int):
    """模拟向量查询操作"""
    await asyncio.sleep(delay_ms / 1000)
    return {"status": "success", "results": 5}


@rate_limit("api_request")
@monitor_latency("api_request")
async def api_request(request_id: int):
    """模拟API请求"""
    await asyncio.sleep(0.05)
    return {"request_id": request_id, "status": "processed"}


async def test_tracing():
    """测试链路追踪功能"""
    print("\n=== 测试链路追踪 ===")
    with tracer.start_span("test_workflow", attributes={"test": "observability"}):
        result1 = await memory_operation(50)
        result2 = await vector_query(30)
        print(f"操作1结果: {result1}")
        print(f"操作2结果: {result2}")
    print("链路追踪测试完成")


async def test_metrics():
    """测试指标监控功能"""
    print("\n=== 测试指标监控 ===")
    
    # 模拟不同延迟的请求
    delays = [10, 20, 30, 40, 50, 100, 150, 200, 5, 8]
    
    for i, delay in enumerate(delays):
        await memory_operation(delay)
        await vector_query(delay * 0.8)
    
    print_metrics_summary()


async def test_rate_limiting():
    """测试速率限制功能"""
    print("\n=== 测试速率限制 ===")
    
    # 配置一个严格的速率限制（每秒2个请求）
    rate_limiter.configure_token_bucket("api_request", capacity=2, rate=2)
    rate_limiter.configure_sliding_window("api_request", window_seconds=10, max_requests=10)
    
    success_count = 0
    failure_count = 0
    
    for i in range(20):
        try:
            result = await api_request(i)
            print(f"请求 {i+1}: {result['status']}")
            success_count += 1
        except RateLimitExceededError as e:
            print(f"请求 {i+1}: 速率限制超出，等待 {e.retry_after:.2f}s")
            failure_count += 1
            # 等待后重试
            await asyncio.sleep(e.retry_after + 0.1)
            try:
                result = await api_request(i)
                print(f"请求 {i+1}(重试): {result['status']}")
                success_count += 1
            except RateLimitExceededError:
                print(f"请求 {i+1}(重试): 仍然超出限制")
    
    print(f"\n速率限制测试完成: 成功 {success_count}, 失败 {failure_count}")


async def main():
    """主测试函数"""
    print("=== 可观测性模块综合测试 ===")
    
    # 设置默认速率限制
    setup_default_rate_limits()
    
    # 运行各项测试
    await test_tracing()
    await test_metrics()
    await test_rate_limiting()
    
    # 输出最终指标摘要
    print("\n=== 最终指标摘要 ===")
    print_metrics_summary()
    
    print("\n=== 所有测试完成 ===")


if __name__ == "__main__":
    asyncio.run(main())
