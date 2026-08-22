#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bayesian AGI Core - 基于自由能原理的认知智能体
"""

__version__ = "1.0.0"
__author__ = "Bayesian AGI Team"

# 导出核心模块
from . import core
from . import utils
from . import services

__all__ = [
    "core",
    "utils",
    "services"
]
