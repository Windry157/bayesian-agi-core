#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
"""

import os
import yaml
from typing import Dict, Any


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """加载配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        配置字典
    """
    if not os.path.exists(config_path):
        # 返回默认配置
        return {
            "app": {
                "debug": False,
                "name": "Bayesian-AGI-Core",
                "version": "1.0.0"
            },
            "models": {
                "default": "minimax-m2.7:cloud",
                "ollama_url": "http://localhost:11434",
                "refresh_interval": 300,
                "providers": {
                    "ollama": {
                        "enabled": True,
                        "models": [
                            "deepseek-r1:7b",
                            "gemma3:4b",
                            "qwen3-vl:4b"
                        ]
                    },
                    "openai": {
                        "enabled": False,
                        "api_key": "",
                        "models": [
                            "gpt-3.5-turbo",
                            "gpt-4"
                        ]
                    }
                }
            },
            "server": {
                "host": "0.0.0.0",
                "port": 8000,
                "workers": 4
            },
            "memory": {
                "directory": "memory",
                "vector_model": "ollama:nomic-embed-text"
            }
        }
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config
