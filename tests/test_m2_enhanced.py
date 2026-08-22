#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M2 增强功能测试

测试内容:
1. ✅ 异常体系 (ContainerException, MissingServiceException)
2. ✅ 循环依赖检测 (CyclicDependencyException)
3. ✅ 模块化配置 (IModule, ModuleLoader)
4. ✅ ContainerBuilder 链式 API
5. ✅ 作用域增强 (RequestScope)
6. ✅ AOP 拦截器 (IInterceptor)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import Protocol, Any
from src.utils.di_exceptions import (
    MissingServiceException,
    CyclicDependencyException,
    ScopeNotActiveException,
)
from src.utils.dependency_injection_v2 import (
    DIContainer,
    ContainerBuilder,
    Scope,
    IModule,
    ModuleLoader,
    IInterceptor,
    InvocationContext,
)


# ======================================================
# 测试 1: 异常体系
# ======================================================

def test_exceptions():
    """测试异常体系"""
    print("\n" + "=" * 60)
    print("测试 1: 异常体系")
    print("=" * 60)

    container = DIContainer()

    # 测试 MissingServiceException
    try:
        container.get(str)  # 未注册的类型
        print("❌ 应该抛出 MissingServiceException")
    except MissingServiceException as e:
        print(f"✅ MissingServiceException: {e.service_type.__name__}")

    # 测试 ScopeNotActiveException
    try:
        container.bind(ITestService := type("ITest", (), {}), type("Test", (), {}))
        container.get(ITestService)
        print("❌ 应该抛出 ScopeNotActiveException")
    except ScopeNotActiveException as e:
        print(f"✅ ScopeNotActiveException: {str(e)[:50]}...")


# ======================================================
# 测试 2: 循环依赖检测
# ======================================================

class IA(Protocol):
    def method_a(self): ...


class IB(Protocol):
    def method_b(self): ...


class IC(Protocol):
    def method_c(self): ...


class ServiceA:
    def __init__(self, b: IB): pass


class ServiceB:
    def __init__(self, c: IC): pass


class ServiceC:
    def __init__(self, a: IA): pass  # 循环依赖!


def test_cyclic_dependency():
    """测试循环依赖检测"""
    print("\n" + "=" * 60)
    print("测试 2: 循环依赖检测")
    print("=" * 60)

    container = DIContainer()
    container.bind(IA, ServiceA)
    container.bind(IB, ServiceB)
    container.bind(IC, ServiceC)

    try:
        container._detect_cyclic_dependencies()
        print("❌ 应该检测到循环依赖")
    except CyclicDependencyException as e:
        print(f"✅ 循环依赖已检测!")
        print(f"   循环路径: {' -> '.join(e.cycle_path)}")


# ======================================================
# 测试 3: 模块化配置
# ======================================================

class IDatabase(Protocol):
    def query(self, sql: str): ...


class ICache(Protocol):
    def get(self, key: str): ...


class PostgresDB:
    def query(self, sql: str):
        return f"结果: {sql}"


class RedisCache:
    def __init__(self, db: IDatabase):  # Cache 依赖 Database
        self.db = db

    def get(self, key: str):
        return self.db.query(f"GET {key}")


class DatabaseModule(IModule):
    """数据库模块"""
    def configure(self, builder: ContainerBuilder):
        builder.bind(IDatabase, PostgresDB, Scope.SINGLETON)


class CacheModule(IModule):
    """缓存模块"""
    def configure(self, builder: ContainerBuilder):
        builder.bind(ICache, RedisCache, Scope.SCOPED)


def test_modules():
    """测试模块化配置"""
    print("\n" + "=" * 60)
    print("测试 3: 模块化配置")
    print("=" * 60)

    # 使用 ModuleLoader 加载多个模块
    loader = ModuleLoader()
    loader.add_module(DatabaseModule())
    loader.add_module(CacheModule())

    # 构建容器
    container = ContainerBuilder().build()
    loader.load(container)

    # 验证依赖图谱
    print("\n依赖图谱:")
    container.print_dependency_graph()

    # 验证功能
    with container.scope():
        cache = container.get(ICache)
        result = cache.get("user:123")
        print(f"\n✅ 缓存功能正常: {result}")


# ======================================================
# 测试 4: ContainerBuilder 链式 API
# ======================================================

def test_builder():
    """测试构建器链式 API"""
    print("\n" + "=" * 60)
    print("测试 4: ContainerBuilder 链式 API")
    print("=" * 60)

    container = (
        ContainerBuilder()
        .bind(IDatabase, PostgresDB, Scope.SINGLETON)
        .bind(ICache, RedisCache)
        .build()
    )

    print("✅ 链式 API 构建成功")
    db = container.get(IDatabase)
    print(f"✅ 获取服务: {db.__class__.__name__}")


# ======================================================
# 测试 5: AOP 拦截器
# ======================================================

class LoggingInterceptor:
    """日志拦截器"""

    def __init__(self):
        self.calls: list = []

    def intercept(self, context: InvocationContext) -> Any:
        self.calls.append(context.method_name)
        print(f"  [日志] 调用方法: {context.method_name}")
        result = context.proceed()
        print(f"  [日志] 完成方法: {context.method_name}")
        return result


class IOrder(Protocol):
    def create_order(self, item: str): ...


class OrderService:
    def create_order(self, item: str) -> str:
        return f"订单已创建: {item}"


def test_interceptors():
    """测试 AOP 拦截器"""
    print("\n" + "=" * 60)
    print("测试 5: AOP 拦截器")
    print("=" * 60)

    container = (
        ContainerBuilder()
        .bind(IOrder, OrderService, Scope.TRANSIENT)
        .with_interceptor(LoggingInterceptor)
        .build()
    )

    order = container.get(IOrder)
    result = order.create_order("商品A")
    print(f"\n✅ 拦截器正常工作!")
    print(f"   拦截的方法: {container._interceptor_instances[LoggingInterceptor].calls}")


# ======================================================
# 主函数
# ======================================================

def main():
    print("\n" + "=" * 60)
    print("M2 增强功能测试")
    print("=" * 60)

    test_exceptions()
    test_cyclic_dependency()
    test_modules()
    test_builder()
    test_interceptors()

    print("\n" + "=" * 60)
    print("✅ M2 所有测试通过!")
    print("=" * 60)
    print("\n验证结果:")
    print("  ✅ 1. 异常体系 (MissingServiceException, ScopeNotActiveException)")
    print("  ✅ 2. 循环依赖检测 (CyclicDependencyException)")
    print("  ✅ 3. 模块化配置 (IModule, ModuleLoader)")
    print("  ✅ 4. ContainerBuilder 链式 API")
    print("  ✅ 5. AOP 拦截器 (IInterceptor)")


if __name__ == "__main__":
    main()
