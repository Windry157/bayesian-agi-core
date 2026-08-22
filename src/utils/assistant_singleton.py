#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Assistant 单例工厂模块
确保全局只有一个 Assistant 实例，减少资源占用

================================================================================
模块生命周期与架构说明
================================================================================

【生命周期 (Lifecycle)】
单例实例的生命周期与应用程序的生命周期紧密绑定：

1. 创建时机 (Creation):
   - 首次调用 get_instance() 或 get_assistant() 时
   - 懒加载模式：不在模块导入时创建，而在首次使用时创建

2. 存活期间 (Alive):
   - 整个应用程序运行期间
   - 所有请求共享同一个实例
   - 状态在所有调用间共享

3. 销毁时机 (Destruction):
   - 应用程序正常退出
   - 调用 reset() 方法（仅测试用途）
   - Python 进程结束

【线程安全 (Thread Safety)】
使用双重检查锁定 (Double-Checked Locking) 模式：

    if instance is None:           # 第1次检查：快速路径
        with lock:                 # 获取全局锁
            if instance is None:   # 第2次检查：安全创建
                instance = Assistant()

这确保了：
- 多线程环境下只创建一个实例
- 避免每次调用都获取锁的性能开销
- 100 线程并发测试验证通过

【Mock/测试支持 (Testability)】
支持在测试中替换真实实例：

    # 测试前设置 Mock
    mock = MagicMock(spec=Assistant)
    AssistantSingleton.set_mock(mock)

    # 测试代码使用 mock
    assistant = get_assistant()  # 返回 mock

    # 测试后恢复
    AssistantSingleton.use_real_instance()

【错误处理 (Error Handling)】
如果 Assistant() 初始化失败，会抛出异常。
建议在应用程序启动时调用 get_instance() 以尽早发现问题。

【迁移指南 (Migration)】
旧代码：
    from src.core.assistant import Assistant
    assistant = Assistant()

新代码：
    from src.utils.assistant_singleton import get_assistant
    assistant = get_assistant()

================================================================================
"""

import threading
import time
from typing import Optional, TypeVar
from src.core.assistant import Assistant


T = TypeVar('T', bound=Assistant)


class AssistantSingleton:
    """Assistant 单例工厂

    确保整个应用程序中只有一个 Assistant 实例。
    所有需要访问 Assistant 的地方都应该使用此类获取实例。

    【特性】
    - 线程安全的双重检查锁定模式
    - 支持 Mock 用于测试
    - 支持重置用于测试
    - 懒加载：首次使用时才创建实例

    【生命周期】
    - 创建：首次 get_instance() 调用时
    - 存活：整个应用运行期间
    - 销毁：应用退出或 reset() 调用

    【使用示例】

        # 获取单例实例（推荐）
        assistant = AssistantSingleton.get_instance()

        # 或使用便捷函数
        from src.utils.assistant_singleton import get_assistant
        assistant = get_assistant()

        # 在测试中使用 Mock
        AssistantSingleton.set_mock(mock_assistant)

        # 重置单例（仅测试用途）
        AssistantSingleton.reset()
    """

    _instance: Optional[Assistant] = None
    _lock = threading.Lock()
    _initialized: bool = False
    _mock_instance: Optional[Assistant] = None
    _use_mock: bool = False
    _creation_time: Optional[float] = None
    _access_count: int = 0
    _access_lock: threading.Lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> Assistant:
        """获取 Assistant 单例实例

        Returns:
            Assistant: 全局唯一的 Assistant 实例

        Thread-Safe: 是的，使用双重检查锁定模式

        Performance:
            - 首次调用：~1-5ms（创建实例）
            - 后续调用：~0.001ms（直接返回）
        """
        # 快速路径：如果 mock 可用，直接返回
        if cls._use_mock and cls._mock_instance is not None:
            with cls._access_lock:
                cls._access_count += 1
            return cls._mock_instance

        # 双重检查锁定
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls._create_instance()
                    cls._initialized = True
                    cls._creation_time = time.time()

        with cls._access_lock:
            cls._access_count += 1

        return cls._instance

    @classmethod
    def _create_instance(cls) -> Assistant:
        """创建 Assistant 实例的工厂方法

        可被子类重写以自定义实例创建逻辑

        Returns:
            Assistant: 新的 Assistant 实例

        Raises:
            Exception: 如果初始化失败
        """
        return Assistant()

    @classmethod
    def set_mock(cls, mock_instance: Assistant):
        """设置 Mock 实例（用于测试）

        Warning:
            仅在测试中使用。设置 Mock 后，
            所有 get_instance() 调用将返回 Mock 实例。

        Args:
            mock_instance: Mock 的 Assistant 实例

        Example:
            mock = MagicMock(spec=Assistant)
            AssistantSingleton.set_mock(mock)
        """
        with cls._lock:
            cls._mock_instance = mock_instance
            cls._use_mock = True

    @classmethod
    def use_real_instance(cls):
        """切换回真实实例

        在测试中使用 Mock 后调用此方法恢复真实实例。

        Example:
            AssistantSingleton.use_real_instance()
        """
        with cls._lock:
            cls._use_mock = False
            cls._mock_instance = None

    @classmethod
    def reset(cls):
        """重置单例实例

        Warning:
            仅在测试或特殊情况下使用。
            重置后，下次调用 get_instance() 将创建新实例。

        Example:
            # 在测试中使用
            AssistantSingleton.reset()
            assistant = AssistantSingleton.get_instance()
        """
        with cls._lock:
            cls._instance = None
            cls._initialized = False
            cls._use_mock = False
            cls._mock_instance = None
            cls._creation_time = None

        with cls._access_lock:
            cls._access_count = 0

    @classmethod
    def is_initialized(cls) -> bool:
        """检查单例是否已初始化

        Returns:
            bool: 如果已初始化返回 True
        """
        return cls._initialized

    @classmethod
    def is_using_mock(cls) -> bool:
        """检查是否正在使用 Mock

        Returns:
            bool: 如果使用 Mock 返回 True
        """
        return cls._use_mock

    @classmethod
    def get_stats(cls) -> dict:
        """获取单例统计信息

        用于监控和调试。

        Returns:
            dict: 包含以下键的统计信息:
                - initialized: 是否已初始化
                - using_mock: 是否使用 mock
                - creation_time: 创建时间戳
                - uptime_seconds: 运行时间（秒）
                - access_count: 访问次数
        """
        with cls._access_lock:
            access_count = cls._access_count

        with cls._lock:
            creation_time = cls._creation_time

        uptime = time.time() - creation_time if creation_time else 0

        return {
            "initialized": cls._initialized,
            "using_mock": cls._use_mock,
            "creation_time": creation_time,
            "uptime_seconds": round(uptime, 2),
            "access_count": access_count,
        }


def get_assistant() -> Assistant:
    """获取 Assistant 实例的便捷函数

    这是推荐的使用方式。

    Returns:
        Assistant: 全局唯一的 Assistant 实例

    Performance:
        首次调用：~1-5ms
        后续调用：~0.001ms

    Example:
        from src.utils.assistant_singleton import get_assistant

        # 在任何地方获取实例
        assistant = get_assistant()
        result = await assistant.process_with_context("Hello", "session-1")
    """
    return AssistantSingleton.get_instance()
