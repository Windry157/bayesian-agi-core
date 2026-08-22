from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class MCPMessage:
    jsonrpc: str = "2.0"
    id: Optional[str] = None

@dataclass
class MCPRequest(MCPMessage):
    method: str = ""
    params: Optional[Dict[str, Any]] = None

@dataclass
class MCPResponse(MCPMessage):
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]] = None

@dataclass
class ResourceDefinition:
    uri: str
    name: str
    description: str
    mime_type: str = "application/json"
