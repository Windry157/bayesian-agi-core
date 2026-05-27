import asyncio
import logging
from typing import List

from .config import GatewayConfig, load_gateway_config
from .channel import ChannelBase
from .mcp_client import MCPClient
from .router import MessageRouter

logger = logging.getLogger("gateway.server")


class GatewayServer:
    def __init__(self, config: GatewayConfig = None):
        self.config = config or GatewayConfig()
        self.client = MCPClient(
            base_url=self.config.engine_url,
            mcp_url=self.config.mcp_url,
        )
        self.router = MessageRouter(self.client)
        self.channels: List[ChannelBase] = []

    def _init_channels(self):
        from .telegram_channel import TelegramChannel

        tg_cfg = self.config.channels.get("telegram", {})
        if tg_cfg.get("enabled") and tg_cfg.get("token"):
            self.channels.append(TelegramChannel(token=tg_cfg["token"], router=self.router))
            logger.info("Telegram channel enabled")

    async def start(self):
        self._init_channels()
        for ch in self.channels:
            await ch.start()
        logger.info(f"Gateway started, {len(self.channels)} channel(s) active")

    async def stop(self):
        for ch in self.channels:
            await ch.stop()
        await self.client.close()
        logger.info("Gateway stopped")


def run_gateway(config_path: str = None):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    config = load_gateway_config(config_path)
    server = GatewayServer(config)
    asyncio.run(server.start())
