#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依赖注入 (DI) 容器 - Phase 2 M1

核心设计原则：
1. 关注"契约"而非"实现" (Interface Segregation)
2. 明确生命周期管理 (Scope Management: Singleton/Scoped/Transient)
3. 自动化与可观测性 (Dependency Graph Visualization)

架构原则：依赖倒置原则 (DIP)
- 高层模块不应该依赖于低层模块，两者都应该依赖于抽象
- 抽象不应该依赖于细节，细节应该依赖于抽象
"""

import threading
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Set,
    Type,
    TypeVar,
    Union,
    Protocol,
)
from enum import Enum
import logging

logger = logging.getLogger(__name__)


T = TypeVar("T")


class Scope(Enum):
    """生命周期作用域"""

    SINGLETON = "singleton"
    """单例：整个应用生命周期内只创建一个实例"""

    SCOPED = "scoped"
    """作用域：在一个特定的业务流程/请求周期内只创建一个实例"""

    TRANSIENT = "transient"
    """瞬时：每次请求或注入时都会创建全新的实例"""


class ServiceDescriptor:
    """服务描述符"""

    def __init__(
        self,
        interface_type: Type[Any],
        implementation_type: Type[Any],
        scope: Scope,
        instance: Optional[Any] = None,
        factory: Optional[Callable[..., Any]] = None,
    ):
        self.interface_type = interface_type
        self.implementation_type = implementation_type
        self.scope = scope
        self.instance = instance
        self.factory = factory
        self.dependencies: List[Type[Any]] = []  # 依赖列表


class DIContainer:
    """依赖注入容器

    特点：
    - 基于接口的依赖注入（DIP 原则）
    - 支持三种生命周期：Singleton/Scoped/Transient
    - 依赖图谱可视化
    """

    def __init__(self):
        self._descriptors: Dict[Type[Any], ServiceDescriptor] = {}
        self._singletons: Dict[Type[Any], Any] = {}
        self._scopes: Dict[int, Dict[Type[Any], Any]] = {}
        self._current_scope_id: Optional[int] = None
        self._scope_counter = 0
        self._lock = threading.Lock()
        self._dependency_graph: Dict[Type[Any], List[Type[Any]]] = {}

    def bind(
        self,
        interface_type: Type[T],
        implementation_type: Type[T],
        scope: Scope = Scope.SINGLETON,
        instance: Optional[T] = None,
        factory: Optional[Callable[..., T]] = None,
    ):
        """绑定接口到实现

        Args:
            interface_type: 接口类型
            implementation_type: 实现类型
            scope: 生命周期作用域
            instance: 预创建的单例实例（可选）
            factory: 工厂函数（可选）
        """
        if instance is not None and scope != Scope.SINGLETON:
            raise ValueError("预创建实例仅支持 SINGLETON 作用域")

        descriptor = ServiceDescriptor(
            interface_type=interface_type,
            implementation_type=implementation_type,
            scope=scope,
            instance=instance,
            factory=factory,
        )

        # 分析依赖关系
        self._analyze_dependencies(descriptor)

        with self._lock:
            self._descriptors[interface_type] = descriptor
            logger.info(
                f"绑定: {interface_type.__name__} -> {implementation_type.__name__}"
                f" [{scope.value}]"
            )

    def get(self, interface_type: Type[T]) -> T:
        """获取服务实例

        Args:
            interface_type: 接口类型

        Returns:
            服务实例

        Raises:
            KeyError: 未找到绑定
        """
        descriptor = self._descriptors.get(interface_type)
        if not descriptor:
            raise KeyError(f"未找到 {interface_type.__name__} 的绑定")

        if descriptor.scope == Scope.SINGLETON:
            return self._get_singleton(descriptor)
        elif descriptor.scope == Scope.SCOPED:
            return self._get_scoped(descriptor)
        else:  # TRANSIENT
            return self._create_instance(descriptor)

    def begin_scope(self) -> int:
        """开始一个新的作用域

        Returns:
            作用域 ID
        """
        with self._lock:
            self._scope_counter += 1
            scope_id = self._scope_counter
            self._scopes[scope_id] = {}
            self._current_scope_id = scope_id
            logger.debug(f"开始作用域: {scope_id}")
            return scope_id

    def end_scope(self, scope_id: Optional[int] = None):
        """结束作用域

        Args:
            scope_id: 作用域 ID（None 表示当前作用域）
        """
        with self._lock:
            if scope_id is None:
                scope_id = self._current_scope_id

            if scope_id in self._scopes:
                del self._scopes[scope_id]
                if self._current_scope_id == scope_id:
                    self._current_scope_id = None
                logger.debug(f"结束作用域: {scope_id}")

    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """获取依赖图谱

        Returns:
            依赖关系图，格式为 {服务: [依赖项]}
        """
        graph = {}
        for interface, desc in self._descriptors.items():
            graph[interface.__name__] = [
                dep.__name__ for dep in desc.dependencies
            ]
        return graph

    def print_dependency_graph(self):
        """打印依赖图谱（可观测性）"""
        graph = self.get_dependency_graph()
        print("\n=== 依赖图谱 ===")
        for service, dependencies in graph.items():
            dep_str = ", ".join(dependencies) if dependencies else "（无依赖）"
            print(f"  {service} -> {dep_str}")
        print("==============")

    def _get_singleton(self, descriptor: ServiceDescriptor) -> Any:
        """获取或创建单例实例"""
        if descriptor.instance is not None:
            return descriptor.instance

        with self._lock:
            if descriptor.interface_type not in self._singletons:
                self._singletons[descriptor.interface_type] = (
                    self._create_instance(descriptor)
                )
            return self._singletons[descriptor.interface_type]

    def _get_scoped(self, descriptor: ServiceDescriptor) -> Any:
        """获取或创建作用域实例"""
        scope_id = self._current_scope_id
        if scope_id is None:
            raise RuntimeError("未在作用域上下文中")

        scope = self._scopes.get(scope_id)
        if scope is None:
            raise RuntimeError(f"作用域 {scope_id} 不存在")

        if descriptor.interface_type not in scope:
            scope[descriptor.interface_type] = self._create_instance(descriptor)

        return scope[descriptor.interface_type]

    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """创建实例"""
        if descriptor.factory:
            return descriptor.factory()

        # 尝试自动解析依赖并创建实例
        return self._auto_resolve(descriptor)

    def _auto_resolve(self, descriptor: ServiceDescriptor) -> Any:
        """自动解析依赖并创建实例"""
        # 简单实现：假设构造函数需要的依赖可以从容器获取
        constructor = descriptor.implementation_type.__init__

        # 获取构造函数的类型提示
        import inspect

        sig = inspect.signature(constructor)
        params = list(sig.parameters.values())[1:]  # 跳过 self

        # 尝试获取所有依赖
        args = []
        for param in params:
            if param.annotation == inspect.Parameter.empty:
                raise ValueError(
                    f"无法自动解析 {descriptor.implementation_type.__name__} "
                    f"的参数 {param.name}：缺少类型注解"
                )
            dep_type = param.annotation
            args.append(self.get(dep_type))

        return descriptor.implementation_type(*args)

    def _analyze_dependencies(self, descriptor: ServiceDescriptor):
        """分析并记录依赖关系"""
        import inspect

        try:
            constructor = descriptor.implementation_type.__init__
            sig = inspect.signature(constructor)
            params = list(sig.parameters.values())[1:]  # 跳过 self

            dependencies = []
            for param in params:
                if param.annotation != inspect.Parameter.empty:
                    dependencies.append(param.annotation)

            descriptor.dependencies = dependencies
            self._dependency_graph[descriptor.interface_type] = dependencies
        except Exception:
            # 无法分析依赖（可能没有类型注解）
            pass


# 全局容器实例
_container: Optional[DIContainer] = None
_container_lock = threading.Lock()


def get_container() -> DIContainer:
    """获取全局容器实例"""
    global _container
    if _container is None:
        with _container_lock:
            if _container is None:
                _container = DIContainer()
    return _container


def set_container(container: DIContainer):
    """设置全局容器实例（用于测试）"""
    global _container
    _container = container


def reset_container():
    """重置容器（用于测试）"""
    global _container
    with _container_lock:
        _container = None
