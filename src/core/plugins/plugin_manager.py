#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件管理器模块
用于加载和管理插件
"""

import os
import sys
import importlib.util
import logging
from typing import Dict, List, Optional, Any
from .plugin_interface import PluginInterface

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PluginManager:
    """插件管理器

    用于加载和管理插件
    """

    def __init__(self):
        """初始化插件管理器"""
        self.plugins: Dict[str, PluginInterface] = {}
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}

    def load_plugin(self, plugin_path: str) -> bool:
        """加载插件

        Args:
            plugin_path: 插件路径

        Returns:
            是否加载成功
        """
        try:
            # 检查插件路径是否存在
            if not os.path.exists(plugin_path):
                logger.error(f"插件路径不存在: {plugin_path}")
                return False

            # 获取插件文件名
            plugin_filename = os.path.basename(plugin_path)
            plugin_name = os.path.splitext(plugin_filename)[0]

            # 加载插件模块
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
            if spec is None:
                logger.error(f"无法创建插件模块规范: {plugin_path}")
                return False

            plugin_module = importlib.util.module_from_spec(spec)
            sys.modules[plugin_name] = plugin_module
            spec.loader.exec_module(plugin_module)

            # 查找插件类
            plugin_class = None
            for name, obj in plugin_module.__dict__.items():
                if (
                    isinstance(obj, type)
                    and issubclass(obj, PluginInterface)
                    and obj is not PluginInterface
                ):
                    plugin_class = obj
                    break

            if plugin_class is None:
                logger.error(f"插件中没有找到实现PluginInterface的类: {plugin_path}")
                return False

            # 创建插件实例
            plugin = plugin_class()

            # 初始化插件
            config = self.plugin_configs.get(plugin_name, {})
            if not plugin.initialize(config):
                logger.error(f"插件初始化失败: {plugin_name}")
                return False

            # 存储插件
            self.plugins[plugin.get_name()] = plugin
            logger.info(
                f"成功加载插件: {plugin.get_name()} (版本: {plugin.get_version()})"
            )
            return True
        except Exception as e:
            logger.error(f"加载插件失败: {e}")
            return False

    def load_plugins_from_directory(self, directory: str) -> List[str]:
        """从目录加载插件

        Args:
            directory: 插件目录

        Returns:
            加载成功的插件列表
        """
        loaded_plugins = []

        if not os.path.exists(directory):
            logger.error(f"插件目录不存在: {directory}")
            return loaded_plugins

        for filename in os.listdir(directory):
            if filename.endswith(".py"):
                plugin_path = os.path.join(directory, filename)
                if self.load_plugin(plugin_path):
                    loaded_plugins.append(filename)

        return loaded_plugins

    def get_plugin(self, plugin_name: str) -> Optional[PluginInterface]:
        """获取插件

        Args:
            plugin_name: 插件名称

        Returns:
            插件实例，如果不存在返回None
        """
        return self.plugins.get(plugin_name)

    def get_all_plugins(self) -> Dict[str, PluginInterface]:
        """获取所有插件

        Returns:
            插件字典
        """
        return self.plugins

    def process_with_plugin(
        self, plugin_name: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """使用插件处理数据

        Args:
            plugin_name: 插件名称
            data: 输入数据

        Returns:
            处理结果，如果插件不存在返回None
        """
        plugin = self.plugins.get(plugin_name)
        if plugin:
            try:
                return plugin.process(data)
            except Exception as e:
                logger.error(f"插件处理数据失败: {e}")
        return None

    def process_with_all_plugins(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """使用所有插件处理数据

        Args:
            data: 输入数据

        Returns:
            处理结果
        """
        result = data.copy()
        for plugin_name, plugin in self.plugins.items():
            try:
                plugin_result = plugin.process(result)
                if plugin_result:
                    result.update(plugin_result)
            except Exception as e:
                logger.error(f"插件 {plugin_name} 处理数据失败: {e}")
        return result

    def set_plugin_config(self, plugin_name: str, config: Dict[str, Any]):
        """设置插件配置

        Args:
            plugin_name: 插件名称
            config: 插件配置
        """
        self.plugin_configs[plugin_name] = config

    def shutdown_all_plugins(self):
        """关闭所有插件"""
        for plugin_name, plugin in self.plugins.items():
            try:
                if plugin.shutdown():
                    logger.info(f"成功关闭插件: {plugin_name}")
                else:
                    logger.error(f"关闭插件失败: {plugin_name}")
            except Exception as e:
                logger.error(f"关闭插件时出错: {e}")
        self.plugins.clear()

    def get_plugin_info(self) -> List[Dict[str, Any]]:
        """获取插件信息

        Returns:
            插件信息列表
        """
        plugin_info = []
        for plugin_name, plugin in self.plugins.items():
            info = {
                "name": plugin.get_name(),
                "version": plugin.get_version(),
                "description": plugin.get_description(),
            }
            plugin_info.append(info)
        return plugin_info
