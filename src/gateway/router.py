import json
import logging
import os
import pathlib
from typing import Dict, Optional

from .channel import IncomingMessage, OutgoingMessage
from .mcp_client import MCPClient

logger = logging.getLogger("gateway.router")


class MessageRouter:
    def __init__(self, mcp_client: MCPClient, state_dir: str = "data/gateway"):
        self.client = mcp_client
        self._sessions: Dict[str, str] = {}
        self._state_dir = pathlib.Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._load_state()

    def _state_path(self) -> str:
        return str(self._state_dir / "sessions.json")

    def _load_state(self):
        path = self._state_path()
        if os.path.exists(path):
            try:
                with open(path) as f:
                    data = json.load(f)
                    self._sessions.update(data)
                    logger.info(f"Loaded {len(data)} persisted sessions")
            except Exception as e:
                logger.warning(f"Failed to load sessions: {e}")

    def _save_state(self):
        try:
            path = self._state_path()
            temp = path + ".tmp"
            with open(temp, "w") as f:
                json.dump(self._sessions, f)
            os.replace(temp, path)
        except Exception as e:
            logger.warning(f"Failed to save sessions: {e}")

    def get_session_id(self, channel: str, user_id: str) -> str:
        return f"{channel}:{user_id}"

    async def route(self, message: IncomingMessage) -> Optional[OutgoingMessage]:
        session_id = self.get_session_id(message.channel, message.channel_user_id)
        self._sessions.setdefault(session_id, "")

        text = message.text.strip()
        if not text:
            return None

        if text.startswith("/"):
            return await self._handle_command(text, message, session_id)
        return await self._handle_chat(text, message, session_id)

    async def _call_with_retry(self, fn, max_retries: int = 2) -> str:
        last_error = ""
        for attempt in range(max_retries + 1):
            try:
                result = await fn()
                if result:
                    return result
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries:
                    logger.warning(f"Retry {attempt + 1}/{max_retries}: {e}")
                    import asyncio
                    await asyncio.sleep(1)
        return last_error or "Service temporarily unavailable."

    async def _handle_chat(self, text: str, msg: IncomingMessage, session_id: str) -> OutgoingMessage:
        async def try_chat():
            return await self.client.chat(text, session_id=session_id)

        response = await self._call_with_retry(try_chat)
        if not response:
            async def try_inference():
                result = await self.client.call_mcp_tool("active_inference", {
                    "current_state": text,
                    "goal_state": "provide helpful response",
                    "available_actions": ["chat", "analyze", "search_memory", "generate_insight"],
                })
                return result.get("text", "")
            response = await self._call_with_retry(try_inference)
        reply = response or "I received your message."
        self._save_state()
        return OutgoingMessage(text=reply, channel=msg.channel, channel_user_id=msg.channel_user_id)

    async def _handle_command(self, text: str, msg: IncomingMessage, session_id: str) -> OutgoingMessage:
        cmd = text.split()[0].lower()
        args = " ".join(text.split()[1:])

        if cmd == "/start":
            reply = "Hello! I am your AI assistant powered by Bayesian-AGI-Core."
        elif cmd == "/help":
            reply = "Commands: /start, /help, /models, /memory <query>, /analyze <code>/<language>"
        elif cmd == "/models":
            models = await self._call_with_retry(self.client.get_models)
            if isinstance(models, list):
                reply = "Available models:\n" + "\n".join(f"- {m}" for m in models) if models else "No models found."
            else:
                reply = str(models)
        elif cmd == "/memory":
            if not args:
                reply = "Usage: /memory <query>"
            else:
                results = await self._call_with_retry(lambda: self.client.search_memory(args))
                if isinstance(results, list):
                    reply = "Memory results:\n" + "\n".join(f"- {r}" for r in results) if results else "No results."
                else:
                    reply = "Memory search failed."
        elif cmd == "/analyze" and "/" in args:
            parts = args.split("/", 1)
            async def try_analyze():
                result = await self.client.call_mcp_tool("evaluate_code_confidence", {
                    "code": parts[0].strip(), "language": parts[1].strip(),
                })
                return result.get("text", "Analysis failed.")
            reply = await self._call_with_retry(try_analyze)
        else:
            fallback = await self._handle_chat(text, msg, session_id)
            reply = fallback.text

        self._save_state()
        return OutgoingMessage(text=reply, channel=msg.channel, channel_user_id=msg.channel_user_id)
