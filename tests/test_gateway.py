"""
Gateway 模块测试
"""
import pytest
from src.gateway import IncomingMessage, OutgoingMessage, ChannelBase
from src.gateway.config import GatewayConfig, load_gateway_config
from src.gateway.mcp_client import MCPClient
from src.gateway.router import MessageRouter


class TestMessages:
    def test_incoming_message(self):
        msg = IncomingMessage(channel="telegram", channel_user_id="123", text="hello")
        assert msg.channel == "telegram"
        assert msg.channel_user_id == "123"
        assert msg.text == "hello"
        assert msg.metadata == {}

    def test_outgoing_message(self):
        msg = OutgoingMessage(text="reply", channel="telegram", channel_user_id="123")
        assert msg.text == "reply"
        assert msg.channel == "telegram"

    def test_incoming_with_session(self):
        msg = IncomingMessage(channel="test", channel_user_id="u1", text="hi", session_id="ses_1")
        assert msg.session_id == "ses_1"


class TestConfig:
    def test_default_config(self):
        cfg = GatewayConfig()
        assert cfg.engine_url == "http://localhost:8000"
        assert cfg.mcp_url == "http://localhost:8090/mcp"
        assert cfg.port == 8500

    def test_telegram_disabled_by_default(self):
        cfg = GatewayConfig()
        assert cfg.channels.get("telegram", {}).get("enabled") is False

    def test_load_from_dict(self):
        cfg = GatewayConfig()
        cfg.channels["telegram"] = {"enabled": True, "token": "test:token"}
        assert cfg.channels["telegram"]["enabled"] is True
        assert cfg.channels["telegram"]["token"] == "test:token"


class TestChannelBase:
    def test_channel_abstract(self):
        with pytest.raises(TypeError):
            ChannelBase()


class TestMCPClient:
    @pytest.mark.asyncio
    async def test_chat_returns_empty_on_failure(self):
        client = MCPClient(base_url="http://localhost:1")
        result = await client.chat("hello")
        assert result == ""

    @pytest.mark.asyncio
    async def test_call_mcp_tool_returns_error_on_failure(self):
        client = MCPClient(mcp_url="http://localhost:1/mcp")
        result = await client.call_mcp_tool("test", {})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_close(self):
        client = MCPClient()
        await client.close()


class TestMessageRouter:
    @pytest.fixture
    def router(self):
        client = MCPClient(base_url="http://localhost:1", mcp_url="http://localhost:1/mcp")
        return MessageRouter(client)

    def test_get_session_id(self, router):
        sid = router.get_session_id("telegram", "user123")
        assert sid == "telegram:user123"

    @pytest.mark.asyncio
    async def test_empty_message_returns_none(self, router):
        msg = IncomingMessage(channel="test", channel_user_id="u1", text="  ")
        result = await router.route(msg)
        assert result is None

    @pytest.mark.asyncio
    async def test_unknown_command_falls_back_to_chat(self, router):
        msg = IncomingMessage(channel="test", channel_user_id="u1", text="/nonexistent")
        result = await router.route(msg)
        assert result is not None
        assert result.channel == "test"

    @pytest.mark.asyncio
    async def test_start_command(self, router):
        msg = IncomingMessage(channel="test", channel_user_id="u1", text="/start")
        result = await router.route(msg)
        assert result is not None
        assert "Hello" in result.text

    @pytest.mark.asyncio
    async def test_help_command(self, router):
        msg = IncomingMessage(channel="test", channel_user_id="u1", text="/help")
        result = await router.route(msg)
        assert result is not None
        assert "Commands" in result.text


class TestWebSocketChannel:
    def test_websocket_channel_import(self):
        from src.gateway.websocket_channel import WebSocketChannel
        assert WebSocketChannel.name == "websocket"


class TestWeChatChannel:
    def test_wechat_channel_import(self):
        from src.gateway.wechat_channel import WeChatChannel
        assert WeChatChannel.name == "wechat"

    def test_verify_signature(self):
        from src.gateway.wechat_channel import WeChatChannel
        from unittest.mock import MagicMock
        ch = WeChatChannel(router=MagicMock(), token="")
        assert ch._verify("sig", "ts", "nonce") is True  # empty token passes

    def test_build_xml_reply(self):
        from src.gateway.wechat_channel import WeChatChannel
        from unittest.mock import MagicMock
        ch = WeChatChannel(router=MagicMock(), token="")
        xml = ch._build_xml_reply("user1", "bot1", "hello world")
        assert "<ToUserName><![CDATA[user1]]></ToUserName>" in xml
        assert "<Content><![CDATA[hello world]]></Content>" in xml
