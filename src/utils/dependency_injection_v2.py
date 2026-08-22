#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依赖注入容器 - M2 增强版

Phase 2 M2 特性:
1. ✅ 完善的异常体系 (ContainerException)
2. ✅ 循环依赖检测 (CyclicDependencyException)
3. ✅ 模块化配置 (IModule, ModuleLoader)
4. ✅ ContainerBuilder 链式 API
5. ✅ 作用域增强 (RequestScope)
6. ✅ AOP 拦截器 (IInterceptor)

架构原则:
- 依赖倒置原则 (DIP)
- 生命周期管理 (Singleton/Scoped/Transient)
- 可观测性 (依赖图谱)
"""

import threading
import time
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
    runtime_checkable,
)
from enum import Enum
from dataclasses import dataclass
from abc import ABC, abstractmethod
import logging

from .di_exceptions import (
    ContainerException,
    MissingServiceException,
    CyclicDependencyException,
    ScopeNotActiveException,
    InvalidRegistrationException,
    ResolutionException,
    InterceptorException,
)
from .di_types import Scope
from .di_input_validator import InputValidator

logger = logging.getLogger(__name__)

T = TypeVar("T")
TService = TypeVar("TService")
TImpl = TypeVar("TImpl")


@dataclass
class ServiceDescriptor:
    """服务描述符"""
    interface_type: Type[Any]
    implementation_type: Type[Any]
    scope: Scope
    instance: Optional[Any] = None
    factory: Optional[Callable[..., Any]] = None
    dependencies: List[Type[Any]] = None
    interceptors: List[Type["IInterceptor"]] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.interceptors is None:
            self.interceptors = []


# =============================================================================
# AOP 拦截器接口
# =============================================================================

@runtime_checkable
class IInterceptor(Protocol):
    """拦截器接口

    用于实现横切关注点（日志、事务、性能监控等）

    使用示例:
        class LoggingInterceptor:
            def intercept(self, context: InvocationContext):
                logger.info(f"调用 {context.method_name}")
                result = context.proceed()
                logger.info(f"完成 {context.method_name}")
                return result
    """

    def intercept(self, context: "InvocationContext") -> Any:
        """拦截方法调用

        Args:
            context: 调用上下文

        Returns:
            方法执行结果
        """
        ...


@dataclass
class InvocationContext:
    """调用上下文

    封装方法调用的所有信息
    """
    instance: Any
    method_name: str
    args: tuple
    kwargs: dict
    _proceed: Callable[[], Any]
    _index: int = 0

    def proceed(self) -> Any:
        """继续执行方法或下一个拦截器"""
        return self._proceed()


# =============================================================================
# 依赖分析辅助函数
# =============================================================================

def _analyze_service_dependencies(descriptor: ServiceDescriptor) -> None:
    """分析并记录服务依赖关系

    Args:
        descriptor: 服务描述符
    """
    import inspect

    try:
        constructor = descriptor.implementation_type.__init__
        sig = inspect.signature(constructor)
        params = list(sig.parameters.values())[1:]

        dependencies = []
        for param in params:
            if param.annotation != inspect.Parameter.empty:
                dependencies.append(param.annotation)

        descriptor.dependencies = dependencies
    except Exception:
        pass


# =============================================================================
# 模块化配置接口
# =============================================================================

class IModule(ABC):
    """模块接口

    用于声明式地配置一组服务

    使用示例:
        class DatabaseModule(IModule):
            def configure(self, builder: "ContainerBuilder"):
                builder.bind(IDatabase, PostgresDatabase, Scope.SINGLETON)
                builder.bind(ICache, RedisCache, Scope.SINGLETON)
    """

    @abstractmethod
    def configure(self, builder: "ContainerBuilder") -> None:
        """配置模块中的服务

        Args:
            builder: 容器构建器
        """
        ...


class ModuleLoader:
    """模块加载器

    负责加载和合并多个模块的配置
    """

    def __init__(self):
        self._modules: List[IModule] = []

    def add_module(self, module: IModule) -> "ModuleLoader":
        """添加模块"""
        self._modules.append(module)
        return self

    def add_modules(self, *modules: IModule) -> "ModuleLoader":
        """批量添加模块"""
        self._modules.extend(modules)
        return self

    def load(self, builder: "ContainerBuilder") -> None:
        """加载所有模块到构建器"""
        for module in self._modules:
            logger.info(f"加载模块: {module.__class__.__name__}")
            module.configure(builder)


# =============================================================================
# ContainerBuilder 链式 API
# =============================================================================

class ContainerBuilder:
    """容器构建器

    提供链式 API 用于配置服务

    使用示例:
        container = (ContainerBuilder()
            .bind(IConfig, Config)
            .bind(IDatabase, PostgresDB)
            .with_interceptor(ILogging)
            .build())
    """

    def __init__(self):
        self._registrations: Dict[Type, ServiceDescriptor] = {}
        self._interceptors: List[Type[IInterceptor]] = []

    def bind(
        self,
        interface_type: Type[T],
        implementation_type: Type[T],
        scope: Scope = Scope.SINGLETON,
        instance: Optional[T] = None,
        factory: Optional[Callable[..., T]] = None,
    ) -> "ContainerBuilder":
        """绑定服务

        Returns:
            self (支持链式调用)
        """
        # 使用输入校验器进行严格校验
        validated = InputValidator.validate_registration(
            interface_type=interface_type,
            implementation_type=implementation_type,
            scope=scope,
            instance=instance,
            factory=factory,
        )

        descriptor = ServiceDescriptor(
            interface_type=validated["interface_type"],
            implementation_type=validated["implementation_type"],
            scope=validated["scope"],
            instance=validated["instance"],
            factory=validated["factory"],
        )

        # 分析依赖关系
        self._analyze_dependencies(descriptor)

        self._registrations[interface_type] = descriptor
        logger.debug(
            f"注册: {interface_type.__name__} -> "
            f"{implementation_type.__name__} [{scope.value}]"
        )
        return self

    def with_interceptor(
        self, interceptor_type: Type[IInterceptor]
    ) -> "ContainerBuilder":
        """添加全局拦截器

        所有服务调用都会经过这个拦截器
        """
        self._interceptors.append(interceptor_type)
        return self

    def _analyze_dependencies(self, descriptor: ServiceDescriptor) -> None:
        """分析并记录依赖关系"""
        _analyze_service_dependencies(descriptor)

    def build(self) -> "DIContainer":
        """构建容器"""
        container = DIContainer()

        # 分析并验证依赖关系
        for interface, descriptor in self._registrations.items():
            container._analyze_dependencies(descriptor)

        # 检测循环依赖
        container._detect_cyclic_dependencies()

        # 注册服务
        for interface, descriptor in self._registrations.items():
            container._descriptors[interface] = descriptor

        # 设置全局拦截器
        container._global_interceptors = self._interceptors

        return container


# =============================================================================
# 核心 DI 容器
# =============================================================================

class ScopeContext:
    """作用域上下文管理器"""

    def __init__(self, container: "DIContainer"):
        self._container = container
        self._scope_id: Optional[int] = None

    def __enter__(self) -> "ScopeContext":
        self._scope_id = self._container.begin_scope()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._scope_id is not None:
            self._container.end_scope(self._scope_id)


class DIContainer:
    """依赖注入容器 - M2 增强版

    特点:
    - 基于接口的依赖注入 (DIP 原则)
    - 三种生命周期: Singleton/Scoped/Transient
    - 循环依赖检测
    - 依赖图谱可视化
    - AOP 拦截器支持
    """

    def __init__(self):
        self._descriptors: Dict[Type, ServiceDescriptor] = {}
        self._singletons: Dict[Type, Any] = {}
        self._scopes: Dict[int, Dict[Type, Any]] = {}
        self._current_scope_id: Optional[int] = None
        self._scope_counter = 0
        self._lock = threading.Lock()
        self._global_interceptors: List[Type[IInterceptor]] = []
        self._interceptor_instances: Dict[Type, IInterceptor] = {}

    def bind(
        self,
        interface_type: Type[T],
        implementation_type: Type[T],
        scope: Scope = Scope.SINGLETON,
        instance: Optional[T] = None,
        factory: Optional[Callable[..., T]] = None,
    ) -> "DIContainer":
        """绑定服务到容器"""
        builder = ContainerBuilder()
        builder.bind(interface_type, implementation_type, scope, instance, factory)
        descriptor = builder._registrations[interface_type]
        # 分析依赖关系
        self._analyze_dependencies(descriptor)
        self._descriptors[interface_type] = descriptor
        return self

    def get(self, interface_type: Type[T]) -> T:
        """获取服务实例"""
        descriptor = self._descriptors.get(interface_type)
        if not descriptor:
            raise MissingServiceException(interface_type)

        if descriptor.scope == Scope.SINGLETON:
            return self._get_singleton(descriptor, interface_type)
        elif descriptor.scope == Scope.SCOPED:
            return self._get_scoped(descriptor, interface_type)
        else:
            return self._create_instance(descriptor)

    def scope(self) -> ScopeContext:
        """创建作用域上下文管理器"""
        return ScopeContext(self)

    def begin_scope(self) -> int:
        """开始新的作用域"""
        with self._lock:
            self._scope_counter += 1
            scope_id = self._scope_counter
            self._scopes[scope_id] = {}
            self._current_scope_id = scope_id
            logger.debug(f"开始作用域: {scope_id}")
            return scope_id

    def end_scope(self, scope_id: Optional[int] = None) -> None:
        """结束作用域"""
        with self._lock:
            if scope_id is None:
                scope_id = self._current_scope_id

            if scope_id in self._scopes:
                del self._scopes[scope_id]
                if self._current_scope_id == scope_id:
                    self._current_scope_id = None
                logger.debug(f"结束作用域: {scope_id}")

    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """获取依赖图谱"""
        graph = {}
        for interface, desc in self._descriptors.items():
            graph[interface.__name__] = [
                dep.__name__ for dep in desc.dependencies
            ]
        return graph

    def print_dependency_graph(self) -> None:
        """打印依赖图谱"""
        graph = self.get_dependency_graph()
        print("\n=== 依赖图谱 ===")
        for service, deps in graph.items():
            dep_str = ", ".join(deps) if deps else "（无依赖）"
            print(f"  {service} -> {dep_str}")
        print("==============")

    def _detect_cyclic_dependencies(self) -> None:
        """检测循环依赖

        使用 DFS 检测图中是否存在环
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[Type, int] = {t: WHITE for t in self._descriptors}
        parent: Dict[Type, Optional[Type]] = {t: None for t in self._descriptors}

        def dfs(node: Type, path: List[str]) -> Optional[List[str]]:
            color[node] = GRAY
            path.append(node.__name__)

            for dep in self._descriptors[node].dependencies:
                if dep not in self._descriptors:
                    continue

                if color.get(dep, WHITE) == GRAY:
                    # 发现循环!
                    cycle_start = path.index(dep.__name__)
                    cycle = path[cycle_start:] + [dep.__name__]
                    raise CyclicDependencyException(cycle)

                if color.get(dep, WHITE) == WHITE:
                    result = dfs(dep, path)
                    if result:
                        return result

            path.pop()
            color[node] = BLACK
            return None

        for node in self._descriptors:
            if color[node] == WHITE:
                result = dfs(node, [])
                if result:
                    raise CyclicDependencyException(result)

    def _analyze_dependencies(self, descriptor: ServiceDescriptor) -> None:
        """分析并记录依赖关系"""
        _analyze_service_dependencies(descriptor)

    def _get_singleton(self, descriptor: ServiceDescriptor, interface: Type) -> Any:
        """获取或创建单例"""
        if descriptor.instance is not None:
            return descriptor.instance

        with self._lock:
            if interface not in self._singletons:
                self._singletons[interface] = self._create_instance(descriptor)
            return self._singletons[interface]

    def _get_scoped(self, descriptor: ServiceDescriptor, interface: Type) -> Any:
        """获取或创建作用域实例"""
        scope_id = self._current_scope_id
        if scope_id is None:
            raise ScopeNotActiveException(interface.__name__)

        scope = self._scopes.get(scope_id)
        if scope is None:
            raise ScopeNotActiveException(interface.__name__)

        if interface not in scope:
            scope[interface] = self._create_instance(descriptor)

        return scope[interface]

    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """创建实例"""
        if descriptor.factory:
            instance = descriptor.factory()
        else:
            instance = self._auto_resolve(descriptor)

        # 应用拦截器
        if descriptor.interceptors or self._global_interceptors:
            instance = self._wrap_with_interceptors(
                instance, descriptor, descriptor.interceptors
            )

        return instance

    def _auto_resolve(self, descriptor: ServiceDescriptor) -> Any:
        """自动解析依赖并创建实例"""
        import inspect

        constructor = descriptor.implementation_type.__init__
        try:
            sig = inspect.signature(constructor)
        except (ValueError, TypeError):
            # 无法获取签名（如 C 扩展类）时直接无参实例化
            return descriptor.implementation_type()

        params = list(sig.parameters.values())[1:]

        args = []
        for param in params:
            # 跳过 *args / **kwargs 变长参数
            if param.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                continue
            if param.annotation == inspect.Parameter.empty:
                # 无注解但有默认值 -> 使用默认值
                if param.default is not inspect.Parameter.empty:
                    continue
                raise ResolutionException(
                    descriptor.implementation_type.__name__,
                    f"参数 {param.name} 缺少类型注解",
                )
            # 跳过 Any 类型（通常用于可选参数）
            if param.annotation is Any:
                continue
            args.append(self.get(param.annotation))

        return descriptor.implementation_type(*args)

    def _wrap_with_interceptors(
        self,
        instance: Any,
        descriptor: ServiceDescriptor,
        interceptor_types: List[Type[IInterceptor]],
    ) -> Any:
        """使用拦截器包装实例，返回透明代理对象"""
        all_interceptors = list(interceptor_types) + list(self._global_interceptors)

        if not all_interceptors:
            return instance

        for interceptor_type in all_interceptors:
            if interceptor_type not in self._interceptor_instances:
                self._interceptor_instances[interceptor_type] = interceptor_type()

        def build_chain(
            method_name: str, args: tuple, kwargs: dict, index: int
        ) -> Callable:
            if index >= len(all_interceptors):
                return lambda: getattr(instance, method_name)(*args, **kwargs)

            def chain():
                ctx = InvocationContext(
                    instance=instance,
                    method_name=method_name,
                    args=args,
                    kwargs=kwargs,
                    _proceed=build_chain(method_name, args, kwargs, index + 1),
                )
                interceptor = self._interceptor_instances[all_interceptors[index]]
                return interceptor.intercept(ctx)

            return chain

        class InterceptorProxy:
            def __getattr__(self, name: str) -> Any:
                if name.startswith("_"):
                    raise AttributeError(name)
                method = getattr(instance, name)
                if not callable(method):
                    return method

                def wrapped(*args, **kwargs):
                    return build_chain(name, args, kwargs, 0)()

                return wrapped

            def __repr__(self):
                return (
                    f"<InterceptorProxy for "
                    f"{descriptor.implementation_type.__name__}>"
                )

        return InterceptorProxy()


# =============================================================================
# 全局容器管理
# =============================================================================

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


def set_container(container: DIContainer) -> None:
    """设置全局容器"""
    global _container
    _container = container


def reset_container() -> None:
    """重置容器（用于测试）"""
    global _container
    with _container_lock:
        _container = None
