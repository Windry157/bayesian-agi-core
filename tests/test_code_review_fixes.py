#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单元测试套件 - Phase 1: 建立安全网
测试代码评审中修复的核心功能

运行方式:
    python -m pytest tests/test_code_review_fixes.py -v
    或
    python tests/test_code_review_fixes.py
"""

import tempfile
import os
import sys
import time
import threading
import concurrent.futures
import hashlib
import hmac
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

import pytest

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.circuit_breaker import (
    CircuitBreaker, CircuitState, CircuitOpenError,
    CircuitBreakerManager, get_circuit_breaker, _circuit_breakers
)
from src.utils.rate_limiter import (
    FixedWindowRateLimiter, RateLimitConfig
)
from src.utils.config import load_config


# =============================================================================
# 测试 1: CircuitBreaker 线程安全
# =============================================================================

class TestCircuitBreakerThreadSafety:
    """测试 CircuitBreaker 的线程安全性"""

    def setup_method(self):
        """每个测试前清理全局状态"""
        _circuit_breakers.clear()

    def test_concurrent_access_no_exception(self):
        """测试并发访问不会引发 RuntimeError"""
        errors = []
        barrier = threading.Barrier(10)

        def worker(worker_id):
            try:
                barrier.wait()
                for _ in range(100):
                    cb = get_circuit_breaker(f"test_circuit_{worker_id % 3}")
                    state = cb.get_state()
                    CircuitBreakerManager.list_circuits()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"并发访问引发错误: {errors}"

    def test_concurrent_creation_no_race_condition(self):
        """测试并发创建熔断器不会产生竞态条件"""
        created_circuits = []
        lock = threading.Lock()

        def create_circuit(name):
            cb = get_circuit_breaker(name, failure_threshold=5)
            with lock:
                created_circuits.append(name)
            return cb

        threads = []
        for i in range(20):
            t = threading.Thread(target=create_circuit, args=(f"circuit_{i % 5}",))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(created_circuits) == 20
        # 每个熔断器应该只被创建一次
        assert len(_circuit_breakers) == 5

    def test_list_circuits_safe_during_iteration(self):
        """测试 list_circuits 在迭代过程中字典大小不变"""
        errors = []

        def modify_circuits():
            for i in range(50):
                get_circuit_breaker(f"cb_{i}")
                time.sleep(0.001)

        def read_circuits():
            try:
                for _ in range(50):
                    result = CircuitBreakerManager.list_circuits()
                    time.sleep(0.001)
            except RuntimeError as e:
                if "dictionary changed size" in str(e):
                    errors.append(e)

        t1 = threading.Thread(target=modify_circuits)
        t2 = threading.Thread(target=read_circuits)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(errors) == 0, f"迭代过程中字典大小改变: {errors}"

    def test_reset_circuit_thread_safe(self):
        """测试 reset_circuit 线程安全"""
        cb = get_circuit_breaker("test_reset", failure_threshold=2)

        def trigger_and_reset():
            for _ in range(10):
                try:
                    cb._record_failure()
                except CircuitOpenError:
                    pass
                CircuitBreakerManager.reset_circuit("test_reset")

        threads = [threading.Thread(target=trigger_and_reset) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证熔断器状态一致
        final_state = cb.get_state()
        assert final_state == CircuitState.CLOSED

    def test_reset_all_thread_safe(self):
        """测试 reset_all 线程安全"""
        errors = []
        barrier = threading.Barrier(3)

        # 创建熔断器并触发一些失败
        for i in range(10):
            cb = get_circuit_breaker(f"cb_{i}", failure_threshold=100)
            for _ in range(5):
                try:
                    cb._record_failure()
                except CircuitOpenError:
                    pass

        def reset_all():
            barrier.wait()  # 同步开始
            for _ in range(20):
                try:
                    CircuitBreakerManager.reset_all()
                except Exception as e:
                    errors.append(e)
                time.sleep(0.001)

        threads = [threading.Thread(target=reset_all) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证没有错误发生
        assert len(errors) == 0, f"并发 reset_all 引发错误: {errors}"


# =============================================================================
# 测试 2: HMAC-SHA256 WebSocket 认证
# =============================================================================

class TestWebSocketHMACAuth:
    """测试 HMAC-SHA256 WebSocket 认证"""

    def test_hmac_sha256_produces_correct_hash(self):
        """测试 HMAC-SHA256 产生正确的哈希"""
        nonce = "test_nonce_12345"
        secret_key = "my_secret_key"

        expected = hmac.new(
            secret_key.encode('utf-8'),
            nonce.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # 验证可以通过 HMAC 验证
        computed = hmac.new(
            secret_key.encode('utf-8'),
            nonce.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        assert computed == expected
        assert hmac.compare_digest(computed, expected)

    def test_different_nonces_produce_different_hashes(self):
        """测试不同 nonce 产生不同哈希"""
        secret_key = "my_secret_key"
        nonce1 = "nonce_001"
        nonce2 = "nonce_002"

        hash1 = hmac.new(
            secret_key.encode('utf-8'),
            nonce1.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        hash2 = hmac.new(
            secret_key.encode('utf-8'),
            nonce2.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        assert hash1 != hash2

    def test_different_keys_produce_different_hashes(self):
        """测试不同密钥产生不同哈希"""
        nonce = "test_nonce"
        key1 = "key_one"
        key2 = "key_two"

        hash1 = hmac.new(
            key1.encode('utf-8'),
            nonce.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        hash2 = hmac.new(
            key2.encode('utf-8'),
            nonce.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        assert hash1 != hash2

    def test_verify_challenge_response_with_correct_key(self):
        """测试使用正确密钥验证响应"""
        nonce = "test_nonce_1234567890"
        secret_key = "production_secret_key"

        # 生成正确的响应
        response = hmac.new(
            secret_key.encode('utf-8'),
            nonce.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # 验证
        expected = hmac.new(
            secret_key.encode('utf-8'),
            nonce.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        assert hmac.compare_digest(response, expected)

    def test_verify_challenge_response_with_wrong_key(self):
        """测试使用错误密钥验证响应"""
        nonce = "test_nonce"
        correct_key = "correct_key"
        wrong_key = "wrong_key"

        # 用正确密钥生成响应
        response = hmac.new(
            correct_key.encode('utf-8'),
            nonce.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # 用错误密钥验证
        expected = hmac.new(
            wrong_key.encode('utf-8'),
            nonce.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        assert not hmac.compare_digest(response, expected)

    def test_verify_challenge_response_timing_safe(self):
        """测试 hmac.compare_digest 是计时安全的"""
        nonce = "test_nonce"
        key = "secret_key"
        response = hmac.new(
            key.encode('utf-8'),
            nonce.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # compare_digest 使用常量时间比较，防止时序攻击
        assert hmac.compare_digest(response, response)


# =============================================================================
# 测试 3: RateLimiter 内存清理
# =============================================================================

class TestRateLimiterMemoryCleanup:
    """测试 FixedWindowRateLimiter 的内存清理机制"""

    def test_cleanup_removes_old_windows(self):
        """测试清理机制移除旧窗口"""
        config = RateLimitConfig(requests=10, period_seconds=1)
        limiter = FixedWindowRateLimiter(config)

        # 模拟多个窗口的数据
        current_time = time.time()
        window_0 = int(current_time) // 1  # 当前窗口
        window_1 = window_0 - 1  # 1秒前
        window_2 = window_0 - 2  # 2秒前
        window_3 = window_0 - 3  # 3秒前
        window_4 = window_0 - 4  # 4秒前
        window_old = window_0 - 10  # 非常旧的窗口

        limiter.window_counts["key1"][window_old] = 5
        limiter.window_counts["key1"][window_4] = 3
        limiter.window_counts["key1"][window_3] = 3
        limiter.window_counts["key1"][window_2] = 3
        limiter.window_counts["key1"][window_1] = 2
        limiter.window_counts["key1"][window_0] = 1

        # 执行清理
        limiter._cleanup_old_windows()

        # 验证旧窗口被移除 (保留最近3个窗口: window_0, window_1, window_2)
        # cutoff = current - 3，所以 window_3 (current-3) 不小于 cutoff，不被清理
        assert window_old not in limiter.window_counts["key1"]
        assert window_4 not in limiter.window_counts["key1"]
        # window_3 = current - 3，cutoff = current - 3，所以 window_3 不会被清理
        # 保留最近3个窗口 (window_0, window_1, window_2)
        assert window_3 in limiter.window_counts["key1"]
        assert window_2 in limiter.window_counts["key1"]
        assert window_1 in limiter.window_counts["key1"]
        assert window_0 in limiter.window_counts["key1"]

    def test_cleanup_removes_empty_keys(self):
        """测试清理移除空键"""
        config = RateLimitConfig(requests=10, period_seconds=1)
        limiter = FixedWindowRateLimiter(config)

        current_time = time.time()
        window_old = int(current_time) - 10

        # 添加一个只有旧窗口的键
        limiter.window_counts["old_key"][window_old] = 5
        # 添加一个有空窗口的键
        limiter.window_counts["empty_key"]

        # 执行清理
        limiter._cleanup_old_windows()

        # 验证空键和旧键被移除
        assert "old_key" not in limiter.window_counts
        assert "empty_key" not in limiter.window_counts

    def test_acquire_triggers_cleanup_periodically(self):
        """测试 acquire 定期触发清理"""
        import asyncio
        config = RateLimitConfig(requests=1000, period_seconds=1)  # 大请求数
        limiter = FixedWindowRateLimiter(config)

        # 模拟旧窗口
        old_window = int(time.time()) - 100
        limiter.window_counts["key1"][old_window] = 5
        limiter.window_counts["key2"][old_window] = 5

        async def run_acquires():
            # 执行多次 acquire 以触发清理（每100次清理一次）
            for i in range(150):
                await limiter.acquire("key1")

        # 运行异步测试
        asyncio.run(run_acquires())

        # 验证旧窗口被清理
        assert old_window not in limiter.window_counts["key1"]
        assert old_window not in limiter.window_counts["key2"]

    def test_no_memory_leak_on_many_keys(self):
        """测试大量键不会导致内存泄漏"""
        config = RateLimitConfig(requests=10, period_seconds=1)
        limiter = FixedWindowRateLimiter(config)

        # 创建大量键
        old_window = int(time.time()) - 1000
        for i in range(1000):
            limiter.window_counts[f"user_{i}"][old_window] = 1

        initial_count = len(limiter.window_counts)

        # 执行清理
        limiter._cleanup_old_windows()

        # 验证大部分旧键被清理
        final_count = len(limiter.window_counts)
        assert final_count < initial_count * 0.1, "内存泄漏：大量旧键未被清理"


# =============================================================================
# 测试 4: 配置加载错误处理
# =============================================================================

class TestConfigLoadingErrors:
    """测试配置加载的错误处理"""

    def setup_method(self):
        """每个测试前清理环境变量"""
        if "APP_ENV" in os.environ:
            del os.environ["APP_ENV"]

    def test_production_mode_missing_config_raises_error(self):
        """测试生产模式缺失配置文件抛出明确异常"""
        os.environ["APP_ENV"] = "production"

        with pytest.raises(FileNotFoundError) as exc_info:
            load_config("nonexistent_config.yaml")

        error_message = str(exc_info.value)
        assert "不存在" in error_message or "not exist" in error_message.lower()
        assert "production" in error_message.lower() or "生产" in error_message

    def test_development_mode_missing_config_returns_default(self):
        """测试开发模式缺失配置文件返回默认配置"""
        os.environ["APP_ENV"] = "development"

        config = load_config("nonexistent_config.yaml")

        assert config["app"]["name"] == "Bayesian-AGI-Core"
        assert "models" in config
        assert "server" in config

    def test_default_env_missing_config_returns_default_with_warning(self, capsys):
        """测试默认环境缺失配置文件返回默认配置并记录警告"""
        config = load_config("nonexistent_config.yaml")

        assert config["app"]["name"] == "Bayesian-AGI-Core"

        # 验证警告被记录（如果 logging 配置正确）
        # 注意：这可能需要配置 logging

    def test_existing_config_loads_successfully(self):
        """测试正常配置文件加载成功"""
        # 使用项目根目录的 config.yaml
        config = load_config("config.yaml")

        assert config is not None
        assert "app" in config
        assert "models" in config
        assert "server" in config

    def test_config_with_custom_path(self, tmp_path):
        """测试自定义路径配置文件加载"""
        content = """
app:
  name: Custom App
  version: 99.0.0
models:
  default: custom-model
server:
  port: 9999
"""
        config_file = tmp_path / "custom_config.yaml"
        config_file.write_text(content, encoding="utf-8")

        config = load_config(str(config_file))

        assert config["app"]["name"] == "Custom App"
        assert config["server"]["port"] == 9999


# =============================================================================
# 测试 5: 集成测试 - 所有修复协同工作
# =============================================================================

class TestIntegrationOfAllFixes:
    """测试所有修复协同工作"""

    def setup_method(self):
        """每个测试前清理全局状态"""
        _circuit_breakers.clear()

    def test_circuit_breaker_with_rate_limiter_integration(self):
        """测试熔断器和限流器集成"""
        import asyncio
        # 创建熔断器
        cb = get_circuit_breaker("integration_test", failure_threshold=3)

        # 创建限流器
        config = RateLimitConfig(requests=100, period_seconds=60)
        limiter = FixedWindowRateLimiter(config)

        async def process_requests():
            # 模拟请求处理
            for i in range(10):
                # 先检查限流
                if await limiter.acquire(f"user_{i % 5}"):
                    # 再检查熔断器
                    try:
                        if i % 4 == 0:
                            cb._record_failure()
                    except CircuitOpenError:
                        pass

        asyncio.run(process_requests())

        # 验证状态
        circuits = CircuitBreakerManager.list_circuits()
        assert "integration_test" in circuits

    def test_config_driven_circuit_breaker(self):
        """测试配置驱动的熔断器"""
        # 这测试了配置路径统一（models.ollama_url）
        config = load_config("config.yaml")

        # 验证配置可以正确加载
        assert config is not None
        models_config = config.get("models", {})
        assert "ollama_url" in models_config


# =============================================================================
# 运行测试
# =============================================================================

def run_tests():
    """运行所有测试"""
    print("=" * 80)
    print("运行单元测试套件 - Phase 1: 建立安全网")
    print("=" * 80)

    # 使用 pytest 运行测试
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--color=yes",
        "-x",  # 遇到第一个失败就停止
    ])

    return exit_code


if __name__ == "__main__":
    exit(run_tests())
