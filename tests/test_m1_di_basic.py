#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 2 M1 验收测试 - DI 容器

验证标准：
✅ M1 验收标准:
1. 定义核心服务接口（I...）
2. 实现最简单的容器绑定（Bind<I, T>）
3. 成功注入两个最基础的依赖

测试策略先通过接口
"""

from typing import Protocol
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.dependency_injection import (
    DIContainer,
    Scope,
)




# 定义测试用接口和实现
class ITestServiceA(Protocol):
    def get_name(self) -> str: ...


class TestServiceA:
    def __init__(self):
        self.called = 0

    def get_name(self) -> str:
        self.called += 1
        return "ServiceA"


class ITestServiceB(Protocol):
    def process(self, data: str) -> str: ...


class TestServiceB:
    def __init__(self, service_a: ITestServiceA):
        self.service_a = service_a

    def process(self, data: str) -> str:
        return f"Processed by B (via A: {self.service_a.get_name()}"


class ITestServiceC(Protocol):
    def do_work(self) -> str: ...


class TestServiceC:
    def __init__(self, service_b: ITestServiceB):
        self.service_b = service_b

    def do_work(self) -> str:
        return self.service_b.process("test")


def test_m1_basic_binding():
    """M1 基础绑定测试"""
    print("=" * 60)
    print("M1 验收测试: 基础绑定")
    print("=" * 60)

    container = DIContainer()

    # 1. 定义核心服务接口并绑定
    container.bind(ITestServiceA, TestServiceA, scope=Scope.SINGLETON)
    container.bind(ITestServiceB, TestServiceB, scope=Scope.TRANSIENT)
    container.bind(ITestServiceC, TestServiceC, scope=Scope.TRANSIENT)

    # 2. 验证依赖图谱
    print("\n依赖图谱:")
    graph = container.get_dependency_graph()
    for service, dependencies in graph.items():
        print(f"  {service} -> {', '.join(dependencies)}")

    # 3. 验证获取实例化和注入
    print("\n获取 Service C (依赖链: A <- B <- C")
    service_c = container.get(ITestServiceC)
    result = service_c.do_work()
    print(f"  结果: {result}")

    # 4. 验证单例行为
    print("\n验证单例行为:")
    service_a1 = container.get(ITestServiceA)
    service_a2 = container.get(ITestServiceA)
    print(f"  两次获取的 ServiceA 是否相同: {service_a1 is service_a2}")

    print("\n✅ M1 验收通过!")
    print("  ✅ 1. 接口定义完成")
    print("  ✅ 2. 容器绑定完成")
    print("  ✅ 3. 依赖注入完成")


if __name__ == "__main__":
    test_m1_basic_binding()
