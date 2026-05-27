from dataclasses import dataclass, field
from typing import Optional
import os
import yaml


@dataclass
class GatewayConfig:
    channels: dict = field(default_factory=lambda: {
        "telegram": {"enabled": False, "token": ""},
        "wechat": {"enabled": False},
    })
    engine_url: str = "http://localhost:8000"
    mcp_url: str = "http://localhost:8090/mcp"
    host: str = "0.0.0.0"
    port: int = 8500
    debug: bool = False


def load_gateway_config(path: str = None) -> GatewayConfig:
    config = GatewayConfig()

    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        gateway_cfg = raw.get("gateway", {})
        if "channels" in gateway_cfg:
            config.channels.update(gateway_cfg["channels"])
        if "engine_url" in gateway_cfg:
            config.engine_url = gateway_cfg["engine_url"]
        if "mcp_url" in gateway_cfg:
            config.mcp_url = gateway_cfg["mcp_url"]
        if "host" in gateway_cfg:
            config.host = gateway_cfg["host"]
        if "port" in gateway_cfg:
            config.port = gateway_cfg["port"]
        if "debug" in gateway_cfg:
            config.debug = gateway_cfg["debug"]

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if token:
        config.channels.setdefault("telegram", {})["token"] = token
        config.channels["telegram"]["enabled"] = True

    return config
