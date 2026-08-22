import httpx
import logging
from typing import Optional

from .error_handler import handle_api_errors

logger = logging.getLogger("gateway.mcp_client")


class MCPClient:
    def __init__(self, base_url: str = "http://localhost:8000", mcp_url: str = "http://localhost:8090/mcp"):
        self.base_url = base_url.rstrip("/")
        self.mcp_url = mcp_url
        self._http = httpx.AsyncClient(timeout=120)

    @handle_api_errors(default_value="", error_message="Chat API call")
    async def chat(self, message: str, session_id: Optional[str] = None) -> str:
        resp = await self._http.post(
            f"{self.base_url}/api/decision",
            json={"message": message, "session_id": session_id},
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("response", data.get("reply", ""))
        return ""

    @handle_api_errors(
        default_value=lambda e: {"error": str(e)},
        error_message="MCP call"
    )
    async def call_mcp_tool(self, tool_name: str, arguments: dict) -> dict:
        request = {
            "jsonrpc": "2.0",
            "id": f"gw-{id(self)}",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        resp = await self._http.post(self.mcp_url, json=request)
        if resp.status_code == 200:
            data = resp.json()
            if "result" in data:
                content = data["result"].get("content", [])
                texts = [c.get("text", "") for c in content if c.get("type") == "text"]
                return {"text": "\n".join(texts)}
            if "error" in data:
                return {"error": data["error"].get("message", str(data["error"]))}
        return {"error": "no response from MCP server"}

    @handle_api_errors(default_value=[], error_message="Models API call")
    async def get_models(self) -> list:
        resp = await self._http.get(f"{self.base_url}/api/models")
        if resp.status_code == 200:
            return resp.json().get("models", [])
        return []

    @handle_api_errors(default_value=[], error_message="Memory search")
    async def search_memory(self, query: str, limit: int = 5) -> list:
        resp = await self._http.post(
            f"{self.base_url}/api/memory/search",
            json={"query": query, "limit": limit},
        )
        if resp.status_code == 200:
            return resp.json().get("results", [])
        return []

    async def close(self):
        await self._http.aclose()
