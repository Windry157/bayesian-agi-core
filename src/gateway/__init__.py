"""
Message Channel Gateway

Routes messages from various messaging platforms (Telegram, WhatsApp, etc.)
to the bayesian-agi-core engine via REST/MCP protocols.
"""

from .channel import ChannelBase, IncomingMessage, OutgoingMessage
from .config import GatewayConfig, load_gateway_config
from .router import MessageRouter

__all__ = [
    "ChannelBase", "IncomingMessage", "OutgoingMessage",
    "GatewayConfig", "load_gateway_config",
    "MessageRouter",
]
