import json
import logging
from typing import Set

from .channel import ChannelBase, IncomingMessage, OutgoingMessage
from .router import MessageRouter

logger = logging.getLogger("gateway.websocket")


class WebSocketChannel(ChannelBase):
    name = "websocket"

    def __init__(self, router: MessageRouter, host: str = "0.0.0.0", port: int = 8510):
        self.router = router
        self.host = host
        self.port = port
        self._server = None
        self._connections: dict = {}

    async def start(self):
        import asyncio
        import uvicorn
        from fastapi import FastAPI, WebSocket, WebSocketDisconnect

        app = FastAPI(title="Gateway WebSocket Channel")

        @app.websocket("/ws")
        async def websocket_endpoint(ws: WebSocket):
            await ws.accept()
            user_id = f"ws:{id(ws)}"
            self._connections[user_id] = ws
            logger.info(f"WebSocket connected: {user_id}")

            try:
                while True:
                    raw = await ws.receive_text()
                    data = json.loads(raw)
                    text = data.get("text", data.get("message", ""))
                    if not text:
                        continue

                    incoming = IncomingMessage(
                        channel="websocket",
                        channel_user_id=user_id,
                        text=text,
                        session_id=data.get("session_id"),
                    )
                    reply = await self.router.route(incoming)
                    if reply:
                        await ws.send_json({"type": "reply", "text": reply.text})
            except (WebSocketDisconnect, Exception) as e:
                logger.info(f"WebSocket disconnected: {user_id}: {e}")
            finally:
                self._connections.pop(user_id, None)

        config = uvicorn.Config(app, host=self.host, port=self.port, log_level="info")
        self._server = uvicorn.Server(config)
        logger.info(f"WebSocket channel starting on {self.host}:{self.port}")
        await self._server.serve()

    async def stop(self):
        if self._server:
            self._server.should_exit = True
        for ws in self._connections.values():
            await ws.close()
        self._connections.clear()
        logger.info("WebSocket channel stopped")

    async def send_message(self, message: OutgoingMessage):
        ws = self._connections.get(message.channel_user_id)
        if ws:
            try:
                await ws.send_json({"type": "reply", "text": message.text})
            except Exception as e:
                logger.error(f"Failed to send WebSocket message: {e}")
