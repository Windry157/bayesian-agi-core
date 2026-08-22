#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DI 容器类型定义 - 阶段 2.1

将核心类型定义放在单独的文件中，避免循环导入。
"""

from enum import Enum


class Scope(Enum):
    """生命周期作用域"""

    SINGLETON = "singleton"
    """单例：整个应用生命周期内只创建一个实例"""

    SCOPED = "scoped"
    """作用域：在一个特定的业务流程/请求周期内只创建一个实例"""

    TRANSIENT = "transient"
    """瞬时：每次请求或注入时都会创建全新的实例"""