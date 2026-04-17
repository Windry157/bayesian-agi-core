#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件系统模块
"""

from .plugin_interface import PluginInterface
from .plugin_manager import PluginManager

__all__ = ["PluginInterface", "PluginManager"]
