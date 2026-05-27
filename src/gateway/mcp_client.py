import httpx
import json
import logging
from typing import Optional

logger = logging.getLogger("gateway.mcp_client")


class MCPClient:
    def __init__(self, base_url: str = "http://localhost:8000", mcp_url: str = "http://localhost:8090/mcp"):
        self.base_url = base_url.rstrip("/")
        self.mcp_url = mcp_url
        self._http = httpx.AsyncClient(timeout=120)

    async def chat(self, message: str, session_id: Optional[str] = None) -> str:
        try:
            resp = await self._http.post(
                f"{self.base_url}/api/decision",
                json={"message": message, "session_id": session_id},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("response", data.get("reply", ""))
        except Exception as e:
            logger.error(f"Chat API call failed: {e}")
        return ""

    async def call_mcp_tool(self, tool_name: str, arguments: dict) -> dict:
        request = {
            "jsonrpc": "2.0",
            "id": f"gw-{id(self)}",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        try:
            resp = await self._http.post(self.mcp_url, json=request)
            if resp.status_code == 200:
                data = resp.json()
                if "result" in data:
                    content = data["result"].get("content", [])
                    texts = [c.get("text", "") for c in content if c.get("type") == "text"]
                    return {"text": "\n".join(texts)}
                if "error" in data:
                    return {"error": data["error"].get("message", str(data["error"]))}
        except Exception as e:
            logger.error(f"MCP call failed: {e}")
            return {"error": str(e)}
        return {"error": "no response from MCP server"}

    async def get_models(self) -> list:
        try:
            resp = await self._http.get(f"{self.base_url}/api/models")
            if resp.status_code == 200:
                return resp.json().get("models", [])
        except Exception as e:
            logger.error(f"Models API call failed: {e}")
        return []

    async def search_memory(self, query: str, limit: int = 5) -> list:
        try:
            resp = await self._http.post(
                f"{self.base_url}/api/memory/search",
                json={"query": query, "limit": limit},
            )
            if resp.status_code == 200:
                return resp.json().get("results", [])
        except Exception as e:
            logger.error(f"Memory search failed: {e}")
        return []

    async def close(self):
        await self._http.aclose()
