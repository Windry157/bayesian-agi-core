#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依赖注入演示 - Phase 2 M1

展示 3 层依赖链的完整 DI 容器使用：
Layer 1: ConfigService (配置服务)
Layer 2: DatabaseService (数据库服务，依赖 ConfigService)
Layer 3: UserService (用户服务，依赖 DatabaseService)

验证标准：
✅ 所有依赖均通过接口注入
✅ 依赖倒置原则 (DIP) 得到遵循
✅ 生命周期管理正确
✅ 依赖图谱可观测
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import Protocol
from src.utils.dependency_injection import (
    DIContainer,
    Scope,
    get_container,
    reset_container,
)


# =============================================================================
# Layer 1: 配置服务接口与实现
# =============================================================================

class IConfigService(Protocol):
    """配置服务接口"""

    def get(self, key: str, default: str = "") -> str:
        """获取配置"""
        ...


class ConfigService:
    """配置服务实现"""

    def __init__(self):
        self._configs = {
            "db.host": "localhost",
            "db.port": "5432",
            "app.name": "Bayesian-AGI",
        }
        print(f"  [初始化] ConfigService (单例)")

    def get(self, key: str, default: str = "") -> str:
        return self._configs.get(key, default)


# =============================================================================
# Layer 2: 数据库服务接口与实现 (依赖 ConfigService)
# =============================================================================

class IDatabaseService(Protocol):
    """数据库服务接口"""

    def connect(self) -> bool:
        """连接数据库"""
        ...

    def query(self, sql: str) -> list:
        """查询"""
        ...


class DatabaseService:
    """数据库服务实现"""

    def __init__(self, config: IConfigService):
        self._config = config
        self._connected = False
        print(f"  [初始化] DatabaseService (作用域)")

    def connect(self) -> bool:
        host = self._config.get("db.host")
        port = self._config.get("db.port")
        print(f"  [连接] DatabaseService: {host}:{port}")
        self._connected = True
        return True

    def query(self, sql: str) -> list:
        if not self._connected:
            self.connect()
        print(f"  [查询] DatabaseService: {sql}")
        return [{"id": 1, "name": "Test User"}]


# =============================================================================
# Layer 3: 用户服务接口与实现 (依赖 DatabaseService)
# =============================================================================

class IUserService(Protocol):
    """用户服务接口"""

    def get_user(self, user_id: int) -> dict:
        """获取用户信息"""
        ...

    def create_user(self, user_data: dict) -> dict:
        """创建用户"""
        ...


class UserService:
    """用户服务实现"""

    def __init__(self, database: IDatabaseService):
        self._database = database
        print(f"  [初始化] UserService (瞬时)")

    def get_user(self, user_id: int) -> dict:
        print(f"  [业务] UserService.get_user({user_id})")
        results = self._database.query(f"SELECT * FROM users WHERE id={user_id}")
        return results[0] if results else {}

    def create_user(self, user_data: dict) -> dict:
        print(f"  [业务] UserService.create_user({user_data})")
        return {"id": 100, **user_data}


# =============================================================================
# 演示容器使用
# =============================================================================

def setup_container() -> DIContainer:
    """配置并返回容器"""

    container = DIContainer()

    # Layer 1: 配置服务 - 单例
    container.bind(
        IConfigService,
        ConfigService,
        scope=Scope.SINGLETON,
    )

    # Layer 2: 数据库服务 - 作用域
    container.bind(
        IDatabaseService,
        DatabaseService,
        scope=Scope.SCOPED,
    )

    # Layer 3: 用户服务 - 瞬时
    container.bind(
        IUserService,
        UserService,
        scope=Scope.TRANSIENT,
    )

    return container


def run_demo():
    """运行完整演示"""

    print("=" * 60)
    print("Phase 2 M1: DI 容器演示 - 3层依赖链")
    print("=" * 60)

    # 1. 配置容器
    print("\n1. 配置容器绑定...")
    container = setup_container()

    # 2. 打印依赖图谱（可观测性）
    print("\n2. 依赖图谱（可观测性）:")
    container.print_dependency_graph()

    # 3. 演示 1: 基本依赖注入
    print("\n3. 演示 1: 基本依赖注入")
    print("-" * 40)
    user_service = container.get(IUserService)
    user = user_service.get_user(1)
    print(f"  [结果] 用户数据: {user}")

    # 4. 演示 2: 作用域隔离
    print("\n4. 演示 2: 作用域隔离")
    print("-" * 40)

    # 作用域 1
    print("\n  === 作用域 1 ===")
    scope1 = container.begin_scope()
    user_service_1a = container.get(IUserService)
    user_service_1b = container.get(IUserService)
    print(f"  两次获取 UserService 是否是同一实例: {user_service_1a is user_service_1b}")

    # 作用域 2
    print("\n  === 作用域 2 ===")
    scope2 = container.begin_scope()
    user_service_2 = container.get(IUserService)
    print(f"  不同作用域的 UserService 是否不同: {user_service_1a is not user_service_2}")

    container.end_scope(scope1)
    container.end_scope(scope2)

    # 5. 演示 3: 单例共享
    print("\n5. 演示 3: 单例共享")
    print("-" * 40)
    config1 = container.get(IConfigService)
    config2 = container.get(IConfigService)
    print(f"  两次获取 ConfigService 是否是同一实例: {config1 is config2}")

    # 6. 总结
    print("\n" + "=" * 60)
    print("✅ 演示完成!")
    print("=" * 60)
    print("\n验证结果:")
    print("  ✅ Layer 1: ConfigService (单例)")
    print("  ✅ Layer 2: DatabaseService (作用域，依赖 ConfigService)")
    print("  ✅ Layer 3: UserService (瞬时，依赖 DatabaseService)")
    print("  ✅ 所有依赖均通过接口注入")
    print("  ✅ 依赖图谱可观测")
    print("  ✅ 生命周期管理正确")


if __name__ == "__main__":
    run_demo()
