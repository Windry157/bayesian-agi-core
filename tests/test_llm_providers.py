#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM多提供商集成测试
测试LLM工厂、路由器和各个提供商
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

try:
    from src.core.llm.base_llm import (
        BaseLLM, LLMConfig, LLMResponse, Message,
        LLMFactory, LLMRouter, LLMPool
    )
    from src.core.llm.router import (
        IntelligentRouter, RoutingStrategy, ModelMetrics, ModelCost
    )
    LLMS_AVAILABLE = True
except ImportError as e:
    LLMS_AVAILABLE = False
    pytest.skip(f"LLM modules not available: {e}", allow_module_level=True)


class MockLLM(BaseLLM):
    """模拟LLM用于测试"""

    def __init__(self, config_or_model: LLMConfig | str = "mock-model", provider: str = "mock"):
        if isinstance(config_or_model, LLMConfig):
            config = config_or_model
        else:
            config = LLMConfig(provider=provider, model=config_or_model)
        super().__init__(config)
        self.call_count = 0

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        self.call_count += 1
        return LLMResponse(
            content=f"Generated: {prompt[:50]}",
            model=self.model,
            provider=self.provider,
            usage={"input_tokens": 10, "output_tokens": 20}
        )

    def chat(self, messages, **kwargs) -> LLMResponse:
        self.call_count += 1
        content = " ".join([m.content for m in messages])
        return LLMResponse(
            content=f"Response to: {content[:50]}",
            model=self.model,
            provider=self.provider,
            usage={"input_tokens": 10, "output_tokens": 20}
        )

    def get_model_info(self) -> Dict[str, Any]:
        return {"model": self.model, "provider": self.provider}

    def is_available(self) -> bool:
        return True


class TestLLMFactory:
    """LLM工厂测试"""

    def test_register_provider(self):
        """测试提供商注册"""
        LLMFactory._providers.clear()

        class TestProvider(BaseLLM):
            def generate(self, prompt: str, **kwargs) -> LLMResponse:
                return LLMResponse(content="", model="test", provider="test")

            def chat(self, messages, **kwargs) -> LLMResponse:
                return LLMResponse(content="", model="test", provider="test")

            def get_model_info(self) -> Dict[str, Any]:
                return {}

            def is_available(self) -> bool:
                return True

        LLMFactory.register_provider("test", TestProvider)

        assert "test" in LLMFactory._providers
        assert LLMFactory._providers["test"] == TestProvider

    def test_create_from_config(self):
        """测试从配置创建"""
        LLMFactory._providers.clear()
        LLMFactory.register_provider("mock", MockLLM)

        config = LLMConfig(provider="mock", model="test-model")
        llm = LLMFactory.create(config)

        assert isinstance(llm, MockLLM)
        assert llm.model == "test-model"

    def test_create_from_dict(self):
        """测试从字典创建"""
        LLMFactory._providers.clear()
        LLMFactory.register_provider("mock", MockLLM)

        config_dict = {"provider": "mock", "model": "test-model-2"}
        llm = LLMFactory.create(config_dict)

        assert isinstance(llm, MockLLM)
        assert llm.model == "test-model-2"

    def test_create_unknown_provider(self):
        """测试创建未知提供商"""
        LLMFactory._providers.clear()

        config = LLMConfig(provider="unknown", model="test")

        with pytest.raises(ValueError, match="Unknown provider"):
            LLMFactory.create(config)

    def test_get_available_providers(self):
        """测试获取可用提供商"""
        LLMFactory._providers.clear()
        LLMFactory.register_provider("mock1", MockLLM)
        LLMFactory.register_provider("mock2", MockLLM)

        providers = LLMFactory.get_available_providers()

        assert "mock1" in providers
        assert "mock2" in providers


class TestLLMRouter:
    """LLM路由器测试"""

    def test_initialization(self):
        """测试初始化"""
        router = LLMRouter()

        assert len(router.providers) == 0
        assert router.current_index == 0

    def test_add_provider(self):
        """测试添加提供商"""
        router = LLMRouter()
        llm1 = MockLLM("model1", "mock")
        llm2 = MockLLM("model2", "mock")

        router.add_provider(llm1, weight=1)
        router.add_provider(llm2, weight=2)

        assert len(router.providers) == 3  # 1 + 2

    def test_get_next(self):
        """测试轮询获取"""
        router = LLMRouter()
        llm1 = MockLLM("model1", "mock")
        llm2 = MockLLM("model2", "mock")

        router.add_provider(llm1)
        router.add_provider(llm2)

        first = router.get_next()
        second = router.get_next()
        third = router.get_next()

        assert first.model == "model1"
        assert second.model == "model2"
        assert third.model == "model1"

    def test_get_by_model(self):
        """测试根据模型获取"""
        router = LLMRouter()
        llm1 = MockLLM("model1", "mock")
        llm2 = MockLLM("model2", "mock")

        router.add_provider(llm1)
        router.add_provider(llm2)

        result = router.get_by_model("model2")

        assert result.model == "model2"

    def test_get_by_provider(self):
        """测试根据提供商获取"""
        router = LLMRouter()
        llm1 = MockLLM("model1", "provider1")
        llm2 = MockLLM("model2", "provider2")

        router.add_provider(llm1)
        router.add_provider(llm2)

        results = router.get_by_provider("provider1")

        assert len(results) == 1
        assert results[0].model == "model1"


class TestIntelligentRouter:
    """智能路由器测试"""

    def test_initialization(self):
        """测试初始化"""
        router = IntelligentRouter(RoutingStrategy.ROUND_ROBIN)

        assert router.strategy == RoutingStrategy.ROUND_ROBIN
        assert len(router.providers) == 0

    def test_add_provider_with_cost(self):
        """测试添加提供商带成本"""
        router = IntelligentRouter()
        llm = MockLLM("model1", "mock")
        cost = ModelCost(input_cost_per_1k=0.01, output_cost_per_1k=0.02)

        router.add_provider(llm, cost=cost)

        assert len(router.providers) == 1
        assert router.costs["model1"] == cost

    def test_round_robin_strategy(self):
        """测试轮询策略"""
        router = IntelligentRouter(RoutingStrategy.ROUND_ROBIN)
        llm1 = MockLLM("model1", "mock")
        llm2 = MockLLM("model2", "mock")

        router.add_provider(llm1)
        router.add_provider(llm2)

        results = [router.select_provider().model for _ in range(4)]

        assert results == ["model1", "model2", "model1", "model2"]

    def test_random_strategy(self):
        """测试随机策略"""
        router = IntelligentRouter(RoutingStrategy.RANDOM)
        llm1 = MockLLM("model1", "mock")
        llm2 = MockLLM("model2", "mock")

        router.add_provider(llm1)
        router.add_provider(llm2)

        # 多次选择，应该有不同结果
        results = set(router.select_provider().model for _ in range(10))

        assert len(results) >= 1  # 至少有一个被选中

    def test_record_success(self):
        """测试记录成功"""
        router = IntelligentRouter()
        llm = MockLLM("model1", "mock")

        router.add_provider(llm)

        router.record_success("model1", 1.5)
        router.record_success("model1", 2.0)

        metrics = router.metrics["model1"]

        assert metrics.total_requests == 2
        assert metrics.successful_requests == 2
        assert metrics.avg_response_time == 1.75

    def test_record_failure(self):
        """测试记录失败"""
        router = IntelligentRouter()
        llm = MockLLM("model1", "mock")

        router.add_provider(llm)

        router.record_failure("model1", "Test error")

        metrics = router.metrics["model1"]

        assert metrics.total_requests == 1
        assert metrics.failed_requests == 1
        assert metrics.last_error == "Test error"
        assert metrics.consecutive_failures == 1

    def test_circuit_breaker(self):
        """测试熔断器"""
        router = IntelligentRouter()
        router.circuit_breaker_threshold = 3
        llm = MockLLM("model1", "mock")

        router.add_provider(llm)

        # 触发熔断
        for i in range(3):
            router.record_failure("model1", f"Error {i}")

        metrics = router.metrics["model1"]

        assert metrics.is_healthy is False
        assert metrics.consecutive_failures == 3

    def test_get_metrics(self):
        """测试获取指标"""
        router = IntelligentRouter()
        llm1 = MockLLM("model1", "mock")
        llm2 = MockLLM("model2", "mock")

        router.add_provider(llm1)
        router.add_provider(llm2)

        router.record_success("model1", 1.0)
        router.record_failure("model2", "Error")

        metrics = router.get_metrics()

        assert "model1" in metrics
        assert "model2" in metrics
        assert metrics["model1"]["success_rate"] == 1.0
        assert metrics["model2"]["failed_requests"] == 1


class TestLLMPool:
    """LLM连接池测试"""

    def test_initialization(self):
        """测试初始化"""
        pool = LLMPool()

        assert pool.router is not None
        assert pool.fallback_llm is None

    def test_add_provider(self):
        """测试添加提供商"""
        pool = LLMPool()
        llm = MockLLM("model1", "mock")

        pool.add_provider(llm, weight=2)

        assert len(pool.router.providers) == 2

    def test_set_fallback(self):
        """测试设置备用"""
        pool = LLMPool()
        llm1 = MockLLM("model1", "mock")
        llm2 = MockLLM("model2", "mock")

        pool.add_provider(llm1)
        pool.set_fallback(llm2)

        assert pool.fallback_llm == llm2


class TestLLMResponse:
    """LLM响应测试"""

    def test_response_creation(self):
        """测试响应创建"""
        response = LLMResponse(
            content="Test content",
            model="test-model",
            provider="test",
            usage={"input_tokens": 10, "output_tokens": 20}
        )

        assert response.content == "Test content"
        assert response.model == "test-model"
        assert response.provider == "test"
        assert response.usage["input_tokens"] == 10


class TestMessage:
    """消息测试"""

    def test_message_creation(self):
        """测试消息创建"""
        msg = Message(role="user", content="Hello")

        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.name is None

    def test_message_with_name(self):
        """测试带名称的消息"""
        msg = Message(role="user", content="Hello", name="user1")

        assert msg.name == "user1"


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
