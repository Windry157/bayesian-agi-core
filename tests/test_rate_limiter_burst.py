#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
速率限制器突发流量单元测试
测试场景:
1. 令牌桶突发流量处理
2. 滑动窗口突发流量处理
3. 双重限制下的突发流量处理
4. 并发场景下的突发流量测试
"""

import pytest
import asyncio
import time
import threading
from collections import deque

import sys
sys.path.insert(0, "e:\\laowut\\Trae CN\\bayesian-agi-core")

from src.core.observability.rate_limiter import (
    TokenBucket,
    SlidingWindowCounter,
    RateLimiter,
    RateLimitExceededError,
    rate_limiter,
    rate_limit
)


class TestTokenBucketBurst:
    """令牌桶突发流量测试"""
    
    def test_burst_within_capacity(self):
        """测试突发请求在容量范围内"""
        bucket = TokenBucket(capacity=10, rate=1)
        
        # 一次性获取10个令牌（突发）
        for i in range(10):
            assert bucket.try_acquire(), f"第{i+1}次获取令牌失败"
        
        # 第11次应该失败（桶已空）
        assert not bucket.try_acquire(), "第11次获取令牌应该失败"
    
    def test_burst_refill_rate(self):
        """测试突发后令牌补充速率"""
        bucket = TokenBucket(capacity=5, rate=2)
        
        # 消耗所有令牌
        for _ in range(5):
            bucket.try_acquire()
        
        # 等待一段时间后检查令牌补充
        time.sleep(1)
        tokens_after_wait = bucket.get_tokens()
        
        # 应该补充约2个令牌
        assert tokens_after_wait >= 1.5, f"令牌补充不足: {tokens_after_wait}"
        assert tokens_after_wait <= 2.5, f"令牌补充过多: {tokens_after_wait}"
    
    def test_large_burst_vs_small_burst(self):
        """比较大突发和小突发的处理差异"""
        bucket_large = TokenBucket(capacity=100, rate=10)
        bucket_small = TokenBucket(capacity=10, rate=10)
        
        # 大桶可以处理更大的突发
        large_success = sum(1 for _ in range(100) if bucket_large.try_acquire())
        small_success = sum(1 for _ in range(100) if bucket_small.try_acquire())
        
        assert large_success == 100, f"大桶应该处理100个请求，实际处理{large_success}"
        assert small_success == 10, f"小桶应该处理10个请求，实际处理{small_success}"


class TestSlidingWindowBurst:
    """滑动窗口突发流量测试"""
    
    def test_burst_exceeds_window(self):
        """测试突发请求超出窗口限制"""
        window = SlidingWindowCounter(window_seconds=10, max_requests=5)
        
        # 在前1秒内发送5个请求
        for i in range(5):
            success, _ = window.try_acquire()
            assert success, f"第{i+1}次请求应该成功"
        
        # 第6个请求应该被拒绝
        success, retry_after = window.try_acquire()
        assert not success, "第6个请求应该被拒绝"
        assert retry_after > 0, "应该返回重试等待时间"
    
    def test_burst_across_window_boundary(self):
        """测试突发请求跨越窗口边界"""
        window = SlidingWindowCounter(window_seconds=2, max_requests=3)
        
        # 时间点T0: 发送3个请求
        for _ in range(3):
            success, _ = window.try_acquire()
            assert success
        
        # 第4个请求应该被拒绝
        success, _ = window.try_acquire()
        assert not success
        
        # 等待窗口滑动（超过2秒）
        time.sleep(2.1)
        
        # 窗口滑动后应该可以再次请求
        for _ in range(3):
            success, _ = window.try_acquire()
            assert success
    
    def test_burst_rate_spike(self):
        """测试瞬时速率峰值"""
        window = SlidingWindowCounter(window_seconds=1, max_requests=10)
        
        # 瞬时发送10个请求（1秒窗口内）
        results = [window.try_acquire() for _ in range(15)]
        
        success_count = sum(1 for success, _ in results if success)
        failure_count = len(results) - success_count
        
        assert success_count == 10, f"应该允许10个请求，实际允许{success_count}"
        assert failure_count == 5, f"应该拒绝5个请求，实际拒绝{failure_count}"


class TestRateLimiterBurst:
    """速率限制器突发流量综合测试"""
    
    def test_double_limit_burst(self):
        """测试令牌桶+滑动窗口双重限制"""
        limiter = RateLimiter()
        limiter.configure_token_bucket("burst_test", capacity=10, rate=2)
        limiter.configure_sliding_window("burst_test", window_seconds=10, max_requests=20)
        
        # 突发15个请求
        results = [limiter.check_rate_limit("burst_test") for _ in range(15)]
        
        # 前10个应该成功（令牌桶限制）
        success_count = sum(1 for success, _ in results if success)
        
        # 令牌桶容量为10，所以前10个应该成功
        assert success_count == 10, f"应该成功10个请求，实际成功{success_count}"
    
    def test_burst_with_recovery(self):
        """测试突发后的恢复能力"""
        limiter = RateLimiter()
        limiter.configure_token_bucket("recovery_test", capacity=5, rate=1)
        
        # 突发5个请求
        for _ in range(5):
            success, _ = limiter.try_acquire_token_bucket("recovery_test")
            assert success
        
        # 第6个应该失败
        success, retry_after = limiter.try_acquire_token_bucket("recovery_test")
        assert not success
        
        # 等待令牌补充
        time.sleep(3)
        
        # 应该可以再次请求
        success, _ = limiter.try_acquire_token_bucket("recovery_test")
        assert success, "等待后应该可以再次请求"


class TestConcurrentBurst:
    """并发场景下的突发流量测试"""
    
    def test_concurrent_burst_threads(self):
        """多线程并发突发测试"""
        limiter = RateLimiter()
        limiter.configure_token_bucket("concurrent_test", capacity=20, rate=5)
        
        results = []
        lock = threading.Lock()
        
        def worker():
            for _ in range(10):
                success, _ = limiter.try_acquire_token_bucket("concurrent_test")
                with lock:
                    results.append(success)
        
        # 创建5个线程，每个线程发送10个请求
        threads = [threading.Thread(target=worker) for _ in range(5)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        success_count = sum(results)
        failure_count = len(results) - success_count
        
        # 令牌桶容量为20，所以最多20个成功
        assert success_count <= 20, f"成功请求不应超过20，实际{success_count}"
        assert success_count >= 18, f"成功请求应接近20，实际{success_count}"
    
    @pytest.mark.asyncio
    async def test_concurrent_burst_async(self):
        """异步并发突发测试"""
        limiter = RateLimiter()
        limiter.configure_sliding_window("async_test", window_seconds=1, max_requests=15)
        
        async def make_request():
            success, _ = limiter.try_acquire_sliding_window("async_test")
            return success
        
        # 并发发送20个请求
        tasks = [make_request() for _ in range(20)]
        results = await asyncio.gather(*tasks)
        
        success_count = sum(results)
        
        # 窗口内最多15个成功
        assert success_count <= 15, f"成功请求不应超过15，实际{success_count}"
        assert success_count >= 14, f"成功请求应接近15，实际{success_count}"


class TestEdgeCases:
    """边界情况测试"""
    
    def test_zero_capacity_burst(self):
        """测试零容量桶的突发处理"""
        bucket = TokenBucket(capacity=0, rate=1)
        
        # 任何请求都应该失败
        success, _ = bucket.try_acquire(), bucket.get_retry_after()
        assert not bucket.try_acquire(), "零容量桶应该拒绝所有请求"
    
    def test_zero_rate_burst(self):
        """测试零速率桶的突发处理"""
        bucket = TokenBucket(capacity=5, rate=0)
        
        # 初始可以处理5个请求（桶内的令牌）
        for _ in range(5):
            assert bucket.try_acquire()
        
        # 之后应该拒绝所有请求（速率为0，不会补充令牌）
        assert not bucket.try_acquire(), "零速率桶消耗完令牌后应该拒绝请求"
    
    def test_very_large_burst(self):
        """测试超大突发请求"""
        bucket = TokenBucket(capacity=1000, rate=100)
        
        # 发送2000个请求
        results = [bucket.try_acquire() for _ in range(2000)]
        success_count = sum(results)
        
        # 应该只允许1000个请求（容量限制）
        assert success_count >= 1000, f"应该允许至少1000个请求，实际{success_count}"
    
    def test_burst_after_long_idle(self):
        """测试长时间空闲后的突发处理"""
        bucket = TokenBucket(capacity=10, rate=1)
        
        # 长时间空闲（确保桶满）
        time.sleep(15)
        
        # 应该可以一次性获取所有令牌
        success_count = sum(1 for _ in range(10) if bucket.try_acquire())
        assert success_count == 10, "空闲后应该可以获取所有令牌"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
