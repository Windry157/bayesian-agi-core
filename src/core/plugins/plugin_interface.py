#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件接口模块
定义插件需要实现的方法
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class PluginInterface(ABC):
    """插件接口

    定义插件需要实现的方法
    """

    @abstractmethod
    def get_name(self) -> str:
        """获取插件名称

        Returns:
            插件名称
        """

    @abstractmethod
    def get_version(self) -> str:
        """获取插件版本

        Returns:
            插件版本
        """

    @abstractmethod
    def get_description(self) -> str:
        """获取插件描述

        Returns:
            插件描述
        """

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化插件

        Args:
            config: 插件配置

        Returns:
            是否初始化成功
        """

    @abstractmethod
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理数据

        Args:
            data: 输入数据

        Returns:
            处理结果
        """

    @abstractmethod
    def shutdown(self) -> bool:
        """关闭插件

        Returns:
            是否关闭成功
        """
