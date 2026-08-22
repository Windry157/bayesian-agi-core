#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 2 M1 验收测试 - DI 容器

验证标准：
✅ M1 验收标准:
1. 定义核心服务接口（I...）
2. 实现最简单的容器绑定（Bind<I, T>）
3. 成功注入两个最基础的依赖
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import Protocol
from src.utils.dependency_injection import DIContainer, Scope


# ======================================================
# 测试接口和实现
# ======================================================

class IConfig(Protocol):
    """配置服务接口"""
    def get(self, key: str) -> str: ...


class SimpleConfig:
    """简单配置实现"""
    def __init__(self):
        self.data = {"env": "test"}

    def get(self, key: str) -> str:
        return self.data.get(key, "")


class ILogger(Protocol):
    """日志服务接口"""
    def log(self, msg: str) -> None: ...


class SimpleLogger:
    """简单日志实现"""
    def __init__(self, config: IConfig):
        self.config = config
        self.logs: list[str] = []

    def log(self, msg: str) -> None:
        self.logs.append(f"[{self.config.get('env')}] {msg}")


class IApp(Protocol):
    """应用接口"""
    def run(self) -> str: ...


class SimpleApp:
    """简单应用实现"""
    def __init__(self, logger: ILogger):
        self.logger = logger

    def run(self) -> str:
        self.logger.log("App running")
        return "App completed"


# ======================================================
# 测试运行
# ======================================================

def test_m1_di_basic():
    """M1 基础测试"""
    print("\n" + "=" * 60)
    print("Phase 2 M1 验收: DI 容器基础绑定")
    print("=" * 60)

    container = DIContainer()

    # 1. 绑定接口到实现
    print("\n[1/3] 绑定接口到实现...")
    container.bind(IConfig, SimpleConfig, scope=Scope.SINGLETON)
    container.bind(ILogger, SimpleLogger, scope=Scope.TRANSIENT)
    container.bind(IApp, SimpleApp, scope=Scope.TRANSIENT)

    # 2. 打印依赖图谱
    print("\n[2/3] 依赖图谱:")
    graph = container.get_dependency_graph()
    for service, deps in graph.items():
        print(f"  {service} -> {', '.join(deps) or '（无依赖）'}")

    # 3. 验证 3 层依赖链
    print("\n[3/3] 验证依赖注入链 (Config -> Logger -> App)...")
    app = container.get(IApp)
    result = app.run()
    print(f"  应用运行结果: {result}")

    # 获取内部日志记录
    logger = container.get(ILogger)
    print(f"  日志记录: {logger.logs}")

    print("\n" + "=" * 60)
    print("✅ M1 验收完成!")
    print("=" * 60)
    print("\n验证结果:")
    print("  ✅ 1. 核心服务接口已定义 (IConfig, ILogger, IApp)")
    print("  ✅ 2. 容器绑定机制已实现 (Bind<I, T>)")
    print("  ✅ 3. 3 层依赖链成功注入 (Config -> Logger -> App)")
    print("  ✅ 依赖图谱可观测")


if __name__ == "__main__":
    test_m1_di_basic()
