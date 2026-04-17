#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例插件
"""

from src.core.plugins import PluginInterface
from typing import Dict, List, Optional, Any


class ExamplePlugin(PluginInterface):
    """示例插件

    展示如何使用插件系统
    """

    def get_name(self) -> str:
        """获取插件名称

        Returns:
            插件名称
        """
        return "ExamplePlugin"

    def get_version(self) -> str:
        """获取插件版本

        Returns:
            插件版本
        """
        return "1.0.0"

    def get_description(self) -> str:
        """获取插件描述

        Returns:
            插件描述
        """
        return "示例插件，展示如何使用插件系统"

    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化插件

        Args:
            config: 插件配置

        Returns:
            是否初始化成功
        """
        self.config = config
        print(f"ExamplePlugin 初始化成功，配置: {config}")
        return True

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理数据

        Args:
            data: 输入数据

        Returns:
            处理结果
        """
        print(f"ExamplePlugin 处理数据: {data}")
        # 处理数据
        data["example_plugin_processed"] = True
        data["example_plugin_version"] = self.get_version()
        return data

    def shutdown(self) -> bool:
        """关闭插件

        Returns:
            是否关闭成功
        """
        print("ExamplePlugin 关闭成功")
        return True
