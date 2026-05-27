import logging
from typing import Dict, Optional
from .channel import IncomingMessage, OutgoingMessage
from .mcp_client import MCPClient

logger = logging.getLogger("gateway.router")


class MessageRouter:
    def __init__(self, mcp_client: MCPClient):
        self.client = mcp_client
        self._sessions: Dict[str, str] = {}

    def get_session_id(self, channel: str, user_id: str) -> str:
        return f"{channel}:{user_id}"

    async def route(self, message: IncomingMessage) -> Optional[OutgoingMessage]:
        session_id = self.get_session_id(message.channel, message.channel_user_id)

        text = message.text.strip()
        if not text:
            return None

        if text.startswith("/"):
            return await self._handle_command(text, message, session_id)
        return await self._handle_chat(text, message, session_id)

    async def _handle_chat(self, text: str, msg: IncomingMessage, session_id: str) -> OutgoingMessage:
        response = await self.client.chat(text, session_id=session_id)
        if not response:
            mcp_result = await self.client.call_mcp_tool("active_inference", {
                "current_state": text,
                "goal_state": "provide helpful response",
                "available_actions": ["chat", "analyze", "search_memory", "generate_insight"],
            })
            response = mcp_result.get("text", "") or mcp_result.get("error", "I received your message.")
        return OutgoingMessage(text=response, channel=msg.channel, channel_user_id=msg.channel_user_id)

    async def _handle_command(self, text: str, msg: IncomingMessage, session_id: str) -> OutgoingMessage:
        cmd = text.split()[0].lower()
        args = " ".join(text.split()[1:])

        if cmd == "/start":
            reply = "Hello! I am your AI assistant powered by Bayesian-AGI-Core."
        elif cmd == "/help":
            reply = "Commands: /start, /help, /models, /memory <query>, /analyze <code/language>"
        elif cmd == "/models":
            models = await self.client.get_models()
            reply = "Available models:\n" + "\n".join(f"- {m}" for m in models) if models else "No models found."
        elif cmd == "/memory":
            results = await self.client.search_memory(args) if args else []
            reply = "Memory results:\n" + "\n".join(f"- {r}" for r in results) if results else "No results."
        elif cmd == "/analyze" and "/" in args:
            parts = args.split("/", 1)
            result = await self.client.call_mcp_tool("evaluate_code_confidence", {
                "code": parts[0].strip(), "language": parts[1].strip(),
            })
            reply = result.get("text", "Analysis failed.")
        else:
            fallback = await self._handle_chat(text, msg, session_id)
            reply = fallback.text
        return OutgoingMessage(text=reply, channel=msg.channel, channel_user_id=msg.channel_user_id)
