import hashlib
import logging
from typing import Optional

from .channel import ChannelBase, IncomingMessage, OutgoingMessage
from .router import MessageRouter

logger = logging.getLogger("gateway.wechat")


class WeChatChannel(ChannelBase):
    name = "wechat"

    def __init__(self, router: MessageRouter, token: str = "", host: str = "0.0.0.0", port: int = 8520):
        self.router = router
        self.token = token
        self.host = host
        self.port = port
        self._server = None

    async def start(self):
        import uvicorn
        from fastapi import FastAPI, Request, Response

        app = FastAPI(title="Gateway WeChat Channel")

        @app.get("/wechat")
        async def verify(request: Request):
            params = dict(request.query_params)
            signature = params.get("signature", "")
            timestamp = params.get("timestamp", "")
            nonce = params.get("nonce", "")
            echostr = params.get("echostr", "")

            if self._verify(signature, timestamp, nonce):
                return Response(content=echostr, media_type="text/plain")
            return Response(content="invalid", status_code=403)

        @app.post("/wechat")
        async def webhook(request: Request):
            import xml.etree.ElementTree as ET

            body = await request.body()
            root = ET.fromstring(body)
            msg_type = root.findtext("MsgType", "")
            from_user = root.findtext("FromUserName", "")
            content = root.findtext("Content", "")

            if msg_type == "text" and content:
                incoming = IncomingMessage(
                    channel="wechat",
                    channel_user_id=from_user,
                    text=content,
                )
                reply = await self.router.route(incoming)
                if reply:
                    xml_reply = self._build_xml_reply(from_user, root.findtext("ToUserName", ""), reply.text)
                    return Response(content=xml_reply, media_type="application/xml")

            return Response(content="success", media_type="text/plain")

        config = uvicorn.Config(app, host=self.host, port=self.port, log_level="info")
        self._server = uvicorn.Server(config)
        logger.info(f"WeChat channel starting on {self.host}:{self.port}")
        await self._server.serve()

    async def stop(self):
        if self._server:
            self._server.should_exit = True
        logger.info("WeChat channel stopped")

    async def send_message(self, message: OutgoingMessage):
        logger.warning("WeChat cannot send proactive messages (server must reply within 5s)")

    def _verify(self, signature: str, timestamp: str, nonce: str) -> bool:
        if not self.token:
            return True
        parts = sorted([self.token, timestamp, nonce])
        digest = hashlib.sha1("".join(parts).encode()).hexdigest()
        return digest == signature

    def _build_xml_reply(self, from_user: str, to_user: str, text: str) -> str:
        import xml.sax.saxutils as saxutils
        safe = saxutils.escape(text)
        return f"""<xml>
<ToUserName><![CDATA[{from_user}]]></ToUserName>
<FromUserName><![CDATA[{to_user}]]></FromUserName>
<CreateTime>{int(__import__('time').time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{safe}]]></Content>
</xml>"""
