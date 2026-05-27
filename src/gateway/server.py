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
        self._tasks: List[asyncio.Task] = []

    def _init_channels(self):
        from .telegram_channel import TelegramChannel
        from .websocket_channel import WebSocketChannel

        tg_cfg = self.config.channels.get("telegram", {})
        if tg_cfg.get("enabled") and tg_cfg.get("token"):
            self.channels.append(TelegramChannel(token=tg_cfg["token"], router=self.router))
            logger.info("Telegram channel enabled")

        ws_cfg = self.config.channels.get("websocket", {"enabled": True})
        if ws_cfg.get("enabled", True):
            ws_port = ws_cfg.get("port", 8510)
            self.channels.append(WebSocketChannel(router=self.router, port=ws_port))
            logger.info(f"WebSocket channel enabled on port {ws_port}")

    async def start(self):
        self._init_channels()
        for ch in self.channels:
            task = asyncio.create_task(ch.start())
            self._tasks.append(task)
            await asyncio.sleep(0.1)
        logger.info(f"Gateway started, {len(self.channels)} channel(s) active")
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def stop(self):
        for ch in self.channels:
            await ch.stop()
        for t in self._tasks:
            t.cancel()
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
