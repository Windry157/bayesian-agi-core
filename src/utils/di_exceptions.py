#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依赖注入容器异常模块 - M2

定义 DI 容器可能抛出的所有异常类型
"""

from typing import List, Type


class ContainerException(Exception):
    """DI 容器基础异常"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class MissingServiceException(ContainerException):
    """未找到服务绑定异常

    当用户尝试获取一个未注册的服务时抛出
    """

    def __init__(self, service_type: Type):
        self.service_type = service_type
        super().__init__(
            f"未找到服务 {service_type.__name__} 的绑定。"
            f"请先使用 container.bind() 注册该服务。"
        )


class CyclicDependencyException(ContainerException):
    """循环依赖异常

    当检测到服务之间存在循环依赖时抛出

    例如:
        A 依赖 B
        B 依赖 C
        C 依赖 A  <- 循环!
    """

    def __init__(self, cycle_path: List[str]):
        self.cycle_path = cycle_path
        cycle_str = " -> ".join(cycle_path)
        super().__init__(
            f"检测到循环依赖: {cycle_str}\n"
            f"请重新设计依赖关系以消除循环。"
        )


class ScopeNotActiveException(ContainerException):
    """作用域未激活异常

    当在作用域上下文外尝试获取 SCOPED 服务时抛出
    """

    def __init__(self, service_name: str):
        super().__init__(
            f"尝试获取作用域服务 {service_name}，但当前没有激活的作用域。\n"
            f"请先调用 container.begin_scope() 激活作用域。"
        )


class InvalidRegistrationException(ContainerException):
    """无效注册异常

    当服务注册配置无效时抛出
    """

    def __init__(self, message: str):
        super().__init__(f"无效的服务注册: {message}")


class ResolutionException(ContainerException):
    """服务解析异常

    当无法解析服务依赖时抛出
    """

    def __init__(self, service_name: str, reason: str):
        super().__init__(
            f"无法解析服务 {service_name}: {reason}"
        )


class InterceptorException(ContainerException):
    """拦截器异常

    当拦截器执行出错时抛出
    """

    def __init__(self, interceptor_name: str, reason: str):
        super().__init__(
            f"拦截器 {interceptor_name} 执行失败: {reason}"
        )
