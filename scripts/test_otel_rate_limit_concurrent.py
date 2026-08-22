#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高并发限流追踪测试脚本
模拟高并发请求场景，验证 OpenTelemetry 能否正确捕获限流触发的链路
"""

import asyncio
import time
import threading
import sys
sys.path.insert(0, "e:\\laowut\\Trae CN\\bayesian-agi-core")

# 先初始化 OpenTelemetry
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
from opentelemetry.sdk.resources import Resource

# 初始化 OpenTelemetry
resource = Resource.create({"service.name": "rate-limit-concurrent-test"})
provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(ConsoleSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

from src.core.observability.rate_limiter import (
    rate_limiter,
    rate_limit,
    RateLimitExceededError
)

# 配置严格的限流规则用于测试
rate_limiter.configure_token_bucket("api_request", capacity=5, rate=2)
rate_limiter.configure_sliding_window("api_request", window_seconds=10, max_requests=15)


@rate_limit("api_request")
async def api_endpoint(request_id: int):
    """模拟API端点"""
    await asyncio.sleep(0.01)  # 模拟处理时间
    return {"request_id": request_id, "status": "success"}


async def simulate_user(user_id: int, request_count: int):
    """模拟单个用户发送请求"""
    success_count = 0
    failure_count = 0
    
    for i in range(request_count):
        try:
            result = await api_endpoint(f"{user_id}-{i}")
            success_count += 1
            # print(f"用户 {user_id} 请求 {i+1}: {result['status']}")
        except RateLimitExceededError as e:
            failure_count += 1
            # print(f"用户 {user_id} 请求 {i+1}: 限流触发，等待 {e.retry_after:.2f}s")
            await asyncio.sleep(e.retry_after * 0.5)  # 等待一段时间后继续
    
    return {"user_id": user_id, "success": success_count, "failure": failure_count}


async def run_concurrent_test(num_users: int, requests_per_user: int):
    """运行并发测试"""
    print(f"=== 开始高并发测试 ===")
    print(f"用户数: {num_users}, 每个用户请求数: {requests_per_user}")
    print(f"总请求数: {num_users * requests_per_user}")
    print(f"限流配置: 令牌桶(容量=5, 速率=2/s), 滑动窗口(10秒内最多15次)")
    print()
    
    start_time = time.time()
    
    # 创建并发任务
    tasks = [simulate_user(i, requests_per_user) for i in range(num_users)]
    results = await asyncio.gather(*tasks)
    
    end_time = time.time()
    
    # 统计结果
    total_success = sum(r["success"] for r in results)
    total_failure = sum(r["failure"] for r in results)
    total_requests = total_success + total_failure
    duration = end_time - start_time
    
    print("=== 测试结果 ===")
    print(f"总请求数: {total_requests}")
    print(f"成功: {total_success}")
    print(f"失败(限流): {total_failure}")
    print(f"成功率: {total_success / total_requests * 100:.2f}%")
    print(f"失败率: {total_failure / total_requests * 100:.2f}%")
    print(f"总耗时: {duration:.2f}秒")
    print(f"吞吐量: {total_requests / duration:.2f} req/s")
    print()
    
    # 输出每个用户的结果
    print("=== 各用户统计 ===")
    for result in results:
        print(f"用户 {result['user_id']}: 成功={result['success']}, 失败={result['failure']}")
    
    return {
        "total_requests": total_requests,
        "success_count": total_success,
        "failure_count": total_failure,
        "duration": duration,
        "throughput": total_requests / duration
    }


def run_sync_test():
    """运行同步测试（用于对比）"""
    print("\n=== 同步测试（对比）===")
    
    @rate_limit("api_request_sync")
    def sync_endpoint(request_id: int):
        time.sleep(0.01)
        return {"request_id": request_id, "status": "success"}
    
    rate_limiter.configure_token_bucket("api_request_sync", capacity=3, rate=1)
    
    success = 0
    failure = 0
    
    for i in range(20):
        try:
            result = sync_endpoint(i)
            success += 1
        except RateLimitExceededError:
            failure += 1
    
    print(f"同步测试结果: 成功={success}, 失败={failure}")


if __name__ == "__main__":
    # 运行异步并发测试
    asyncio.run(run_concurrent_test(num_users=10, requests_per_user=20))
    
    # 运行同步测试
    run_sync_test()
    
    print("\n=== 测试完成 ===")
    print("OpenTelemetry 追踪数据已输出到控制台")
    print("请检查输出中是否包含 rate_limit.* 的 span")
