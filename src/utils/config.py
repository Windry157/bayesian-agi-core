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

    Raises:
        FileNotFoundError: 如果配置文件不存在且不是开发环境

    Note:
        在生产环境中，配置文件缺失会导致服务启动失败。
        在开发环境中，会返回最小配置但会记录警告。
    """
    if not os.path.exists(config_path):
        # 生产环境：必须使用配置文件
        if os.getenv("APP_ENV") == "production":
            raise FileNotFoundError(
                f"配置文件 '{config_path}' 不存在！生产环境必须提供有效的配置文件。"
                f"请确保 config.yaml 文件存在且格式正确。"
            )

        # 开发环境：使用默认配置但记录警告
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f"配置文件 '{config_path}' 不存在，使用默认配置。"
            f"注意：默认配置不包含 resilience、wechat 等高级功能。"
            f"生产环境应该提供完整的配置文件。"
        )

        return {
            "app": {"debug": False, "name": "Bayesian-AGI-Core", "version": "1.0.0"},
            "models": {
                "default": "llama3.1:8b",
                "ollama_url": os.getenv("OLLAMA_URL", "http://localhost:11434"),
                "refresh_interval": 300,
                "providers": {
                    "ollama": {
                        "enabled": True,
                        "models": ["llama3.1:8b", "qwen3.5:9b", "gemma4:e4b", "deepseek-coder-v2:16b", "codellama:7b"],
                    },
                    "openai": {
                        "enabled": False,
                        "api_key": "",
                        "models": ["gpt-3.5-turbo", "gpt-4"],
                    },
                },
            },
            "server": {"host": "0.0.0.0", "port": 8000, "workers": 4},
            "memory": {
                "directory": "memory",
                "vector_model": "ollama:nomic-embed-text",
            },
            "websocket": {
                "auth_secret": os.getenv("WEBSOCKET_AUTH_SECRET", "CHANGE_ME_IN_PRODUCTION"),
            },
        }

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    def _resolve_env_vars(d):
        import re
        if isinstance(d, str):
            return re.sub(r'\$\{(\w+)(?::-(.*?))?\}',
                          lambda m: os.getenv(m.group(1), m.group(2) or ""), d)
        if isinstance(d, dict):
            return {k: _resolve_env_vars(v) for k, v in d.items()}
        if isinstance(d, list):
            return [_resolve_env_vars(v) for v in d]
        return d
    config = _resolve_env_vars(config)

    # 环境变量覆盖 Ollama 地址
    ollama_url_env = os.getenv("OLLAMA_URL", "")
    if ollama_url_env:
        config.setdefault("models", {})["ollama_url"] = ollama_url_env

    # 兼容处理: wechat 和 feishu 是同一配置的不同名称
    if "wechat" in config and "feishu" not in config:
        config["feishu"] = config["wechat"]
    elif "wechat" not in config and "feishu" in config:
        config["wechat"] = config["feishu"]

    if "feishu" not in config:
        config["feishu"] = {"enabled": False, "app_id": "", "app_secret": ""}
    feishu = config["feishu"]
    import re
    _env_sub = lambda v: re.sub(r'\$\{(\w+)(?::-(.*?))?\}', lambda m: os.getenv(m.group(1), m.group(2) or ""), v) if isinstance(v, str) else v
    feishu["app_id"] = _env_sub(feishu.get("app_id", "")) or os.getenv("FEISHU_APP_ID", "")
    feishu["app_secret"] = _env_sub(feishu.get("app_secret", "")) or os.getenv("FEISHU_APP_SECRET", "")
    feishu["encrypt_key"] = _env_sub(feishu.get("encrypt_key", "")) or os.getenv("FEISHU_ENCRYPT_KEY", "")
    feishu["verification_token"] = _env_sub(feishu.get("verification_token", "")) or os.getenv("FEISHU_VERIFICATION_TOKEN", "")

    # 同步 wechat 配置：只在 wechat 不存在时才用 feishu 覆盖
    if "wechat" not in config:
        config["wechat"] = feishu

    # 处理 websocket 配置
    if "websocket" not in config:
        config["websocket"] = {}
    websocket = config["websocket"]
    secret = websocket.get("auth_secret") or os.getenv("WEBSOCKET_AUTH_SECRET", "")
    if not secret:
        secret = os.getenv("WEBSOCKET_AUTH_SECRET", "")
    if not secret and os.getenv("APP_ENV") == "production":
        raise RuntimeError("WEBSOCKET_AUTH_SECRET must be set in production")
    websocket["auth_secret"] = secret or "CHANGE_ME_IN_PRODUCTION"

    return config
