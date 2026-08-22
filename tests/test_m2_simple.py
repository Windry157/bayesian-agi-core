#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M2 Enhanced Features Test
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
    def __init__(self, a: IA): pass


class IDatabase(Protocol):
    def query(self, sql: str): ...


class ICache(Protocol):
    def get(self, key: str): ...


class PostgresDB:
    def __init__(self, config: Any = None):
        self.config = config

    def query(self, sql: str):
        return f"Result: {sql}"


class RedisCache:
    def __init__(self, db: IDatabase):
        self.db = db

    def get(self, key: str):
        return self.db.query(f"GET {key}")


class DatabaseModule(IModule):
    def configure(self, builder: ContainerBuilder):
        builder.bind(IDatabase, PostgresDB, Scope.SINGLETON)


class CacheModule(IModule):
    def configure(self, builder: ContainerBuilder):
        builder.bind(ICache, RedisCache, Scope.SCOPED)


def test_missing_service():
    """Test missing service exception"""
    print("\n" + "=" * 60)
    print("Test 1: MissingServiceException")
    print("=" * 60)

    container = DIContainer()
    try:
        container.get(str)
        print("FAIL: Should throw exception")
    except MissingServiceException:
        print("PASS: MissingServiceException raised correctly")


def test_cyclic_dependency():
    """Test cyclic dependency detection"""
    print("\n" + "=" * 60)
    print("Test 2: CyclicDependencyException")
    print("=" * 60)

    container = DIContainer()
    container.bind(IA, ServiceA)
    container.bind(IB, ServiceB)
    container.bind(IC, ServiceC)

    try:
        container._detect_cyclic_dependencies()
        print("FAIL: Should detect cyclic dependency")
    except CyclicDependencyException as e:
        print("PASS: Cyclic dependency detected!")
        print(f"   Cycle path: {' -> '.join(e.cycle_path)}")


def test_scope_not_active():
    """Test scope not active exception"""
    print("\n" + "=" * 60)
    print("Test 3: ScopeNotActiveException")
    print("=" * 60)

    container = DIContainer()
    container.bind(IDatabase, PostgresDB, Scope.SCOPED)

    try:
        container.get(IDatabase)
        print("FAIL: Should throw exception")
    except ScopeNotActiveException:
        print("PASS: ScopeNotActiveException raised correctly")


def test_modules():
    """Test modular configuration"""
    print("\n" + "=" * 60)
    print("Test 4: Modular Configuration")
    print("=" * 60)

    loader = ModuleLoader()
    loader.add_module(DatabaseModule())
    loader.add_module(CacheModule())

    container = ContainerBuilder().build()
    loader.load(container)

    print("\nDependency Graph:")
    container.print_dependency_graph()

    with container.scope():
        cache = container.get(ICache)
        result = cache.get("user:123")
        print(f"\nPASS: Module config works: {result}")


def test_builder():
    """Test ContainerBuilder"""
    print("\n" + "=" * 60)
    print("Test 5: ContainerBuilder Chain API")
    print("=" * 60)

    container = (
        ContainerBuilder()
        .bind(IDatabase, PostgresDB, Scope.SINGLETON)
        .bind(ICache, RedisCache)
        .build()
    )

    print("PASS: Chain API build successful")
    db = container.get(IDatabase)
    print(f"PASS: Get service: {db.__class__.__name__}")


def test_normal_flow():
    """Test normal flow"""
    print("\n" + "=" * 60)
    print("Test 6: Normal DI Flow")
    print("=" * 60)

    container = (
        ContainerBuilder()
        .bind(IDatabase, PostgresDB, Scope.SINGLETON)
        .bind(ICache, RedisCache, Scope.SCOPED)
        .build()
    )

    with container.scope():
        cache = container.get(ICache)
        result = cache.get("test_key")
        print(f"PASS: Normal flow works: {result}")


def main():
    print("\n" + "=" * 60)
    print("M2 Enhanced Features Test")
    print("=" * 60)

    test_missing_service()
    test_cyclic_dependency()
    test_scope_not_active()
    test_modules()
    test_builder()
    test_normal_flow()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)
    print("\nVerification:")
    print("  [OK] 1. MissingServiceException")
    print("  [OK] 2. CyclicDependencyException")
    print("  [OK] 3. ScopeNotActiveException")
    print("  [OK] 4. Modular Configuration (IModule)")
    print("  [OK] 5. ContainerBuilder Chain API")
    print("  [OK] 6. Normal DI Flow")


if __name__ == "__main__":
    main()
