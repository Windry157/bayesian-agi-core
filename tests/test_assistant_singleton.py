#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单元测试 - Assistant 单例模式测试
"""

import pytest
import threading
from pathlib import Path
from unittest.mock import MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.assistant_singleton import (
    AssistantSingleton, get_assistant
)


class TestAssistantSingleton:
    """测试 Assistant 单例模式"""

    def setup_method(self):
        """每个测试前重置单例"""
        AssistantSingleton.reset()
        AssistantSingleton.use_real_instance()

    def teardown_method(self):
        """每个测试后重置单例"""
        AssistantSingleton.reset()
        AssistantSingleton.use_real_instance()

    def test_singleton_returns_same_instance(self):
        """测试单例返回相同实例"""
        instance1 = AssistantSingleton.get_instance()
        instance2 = AssistantSingleton.get_instance()

        assert instance1 is instance2, "单例应返回相同实例"

    def test_get_assistant_convenience_function(self):
        """测试便捷函数返回单例"""
        instance1 = get_assistant()
        instance2 = AssistantSingleton.get_instance()

        assert instance1 is instance2, "便捷函数应返回单例"

    def test_is_initialized_after_first_call(self):
        """测试首次调用后标记为已初始化"""
        assert not AssistantSingleton.is_initialized()

        AssistantSingleton.get_instance()

        assert AssistantSingleton.is_initialized()

    def test_reset_clears_instance(self):
        """测试重置清除实例"""
        instance1 = AssistantSingleton.get_instance()
        AssistantSingleton.reset()

        assert not AssistantSingleton.is_initialized()

        instance2 = AssistantSingleton.get_instance()

        assert instance1 is not instance2, "重置后应创建新实例"

    def test_concurrent_access_returns_same_instance(self):
        """测试并发访问返回相同实例"""
        instances = []
        lock = threading.Lock()

        def get_instance():
            instance = AssistantSingleton.get_instance()
            with lock:
                instances.append(instance)

        threads = [threading.Thread(target=get_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(set(instances)) == 1, "并发访问应返回相同实例"

    def test_thread_safety_no_race_condition(self):
        """测试线程安全，无竞态条件"""
        errors = []

        def worker():
            try:
                instance = AssistantSingleton.get_instance()
                assert instance is not None
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"线程安全测试失败: {errors}"

    def test_mock_replaces_real_instance(self):
        """测试 Mock 替换真实实例"""
        mock_assistant = MagicMock()

        AssistantSingleton.set_mock(mock_assistant)

        instance = AssistantSingleton.get_instance()

        assert instance is mock_assistant
        assert AssistantSingleton.is_using_mock()

    def test_mock_then_restore_real_instance(self):
        """测试使用 Mock 后恢复真实实例"""
        real_instance = AssistantSingleton.get_instance()
        mock_assistant = MagicMock()

        AssistantSingleton.set_mock(mock_assistant)
        assert AssistantSingleton.get_instance() is mock_assistant

        AssistantSingleton.use_real_instance()
        assert AssistantSingleton.get_instance() is real_instance
        assert not AssistantSingleton.is_using_mock()

    def test_mock_concurrent_access(self):
        """测试 Mock 模式下并发访问安全"""
        mock_assistant = MagicMock()
        AssistantSingleton.set_mock(mock_assistant)

        instances = []

        def get_instance():
            instance = AssistantSingleton.get_instance()
            instances.append(instance)

        threads = [threading.Thread(target=get_instance) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(i is mock_assistant for i in instances)
        assert len(set(instances)) == 1

    def test_reset_clears_mock_state(self):
        """测试重置清除 Mock 状态"""
        mock_assistant = MagicMock()
        AssistantSingleton.set_mock(mock_assistant)

        AssistantSingleton.reset()

        assert not AssistantSingleton.is_initialized()
        assert not AssistantSingleton.is_using_mock()
        assert AssistantSingleton.get_instance() is not mock_assistant


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
