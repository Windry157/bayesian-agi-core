import json
import os
import logging
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.mcp.common import DATA_DIR
from src.mcp.server import BayesianMCPServer
from src.mcp.protocol import MCPRequest

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL")
server = BayesianMCPServer(host="0.0.0.0", port=8090, redis_url=REDIS_URL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await server.start_dispatcher()
    yield
    await server.dispatcher.stop()


app = FastAPI(title="Bayesian-AGI-Core MCP Server", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return JSONResponse(server.get_server_info())


@app.get("/health")
async def health():
    return {"status": "healthy", "server": "BayesianAGICore", "version": "2.0.0"}


@app.get("/health/detailed")
async def detailed_health():
    return {
        "status": "healthy", "server": "BayesianAGICore", "version": "2.0.0",
        "uptime": 0,
        "checks": {"memory_store": "ok", "bug_database": "ok", "tools": f"{len(server.tools)} tools"},
        "metrics": {
            "tools_count": len(server.tools), "resources_count": len(server.resources),
            "memory_items": len(server.memory.items), "bug_entries": len(server.bug_db.bugs)
        }
    }


@app.get("/tools")
async def list_tools():
    return JSONResponse({"tools": [{"name": t.name, "description": t.description, "inputSchema": t.input_schema} for t in server.tools.values()]})


@app.get("/resources")
async def list_resources():
    return JSONResponse({"resources": [{"uri": r.uri, "name": r.name, "description": r.description, "mimeType": r.mime_type} for r in server.resources.values()]})


@app.post("/flush")
async def flush():
    await server.dispatcher.flush_all(server.memory, server.bug_db)
    return {"status": "flushed"}


@app.get("/tasks")
async def task_stats():
    return {
        "queue_size": server.dispatcher.queue.qsize(),
        "workers": len(server.dispatcher.workers),
        "redis_connected": server.dispatcher._redis is not None,
    }


@app.get("/metrics")
async def metrics():
    mem = server.memory.get_stats()
    bug = server.bug_db.get_stats()
    qsize = server.dispatcher.queue.qsize()
    lines = [
        "# HELP bayesian_tools_total Number of registered MCP tools",
        "# TYPE bayesian_tools_total gauge",
        f"bayesian_tools_total {len(server.tools)}",
        "",
        "# HELP bayesian_memory_items Total memory items by layer",
        "# TYPE bayesian_memory_items gauge",
        f'bayesian_memory_items{{layer="short_term"}} {mem.get("short_term_count", 0)}',
        f'bayesian_memory_items{{layer="medium_term"}} {mem.get("medium_term_count", 0)}',
        f'bayesian_memory_items{{layer="long_term"}} {mem.get("long_term_count", 0)}',
        "",
        "# HELP bayesian_memory_free_energy Current free energy value",
        "# TYPE bayesian_memory_free_energy gauge",
        f"bayesian_memory_free_energy {mem.get('free_energy', 0)}",
        "",
        "# HELP bayesian_memory_avg_importance Average importance across all items",
        "# TYPE bayesian_memory_avg_importance gauge",
        f"bayesian_memory_avg_importance {mem.get('avg_importance', 0)}",
        "",
        "# HELP bayesian_bugs_total Total bug entries",
        "# TYPE bayesian_bugs_total gauge",
        f"bayesian_bugs_total {bug.get('total_bugs', 0)}",
        "",
        "# HELP bayesian_index_terms Number of indexed terms in TF-IDF",
        "# TYPE bayesian_index_terms gauge",
        f"bayesian_index_terms {mem.get('index_stats', {}).get('indexed_terms', 0)}",
        "",
        "# HELP bayesian_task_queue_size Current task queue depth",
        "# TYPE bayesian_task_queue_size gauge",
        f"bayesian_task_queue_size {qsize}",
        "",
        "# HELP bayesian_workers_active Number of active task workers",
        "# TYPE bayesian_workers_active gauge",
        f"bayesian_workers_active {len(server.dispatcher.workers)}",
        "",
        "# HELP bayesian_redis_connected Whether Redis backend is connected",
        "# TYPE bayesian_redis_connected gauge",
        f"bayesian_redis_connected {1 if server.dispatcher._redis is not None else 0}",
        "",
    ]
    return PlainTextResponse("\n".join(lines), media_type="text/plain")


@app.post("/mcp")
async def handle_mcp(request: Request):
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return JSONResponse({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}, status_code=400)
    mcp_request = MCPRequest(id=body.get("id"), method=body.get("method", ""), params=body.get("params"))
    response = await server.handle_request(mcp_request)
    resp_dict = {k: v for k, v in asdict(response).items() if v is not None}
    return JSONResponse(resp_dict)


@app.get("/mcp")
async def mcp_get():
    return JSONResponse(server.get_server_info())


def start_server(host: str = "0.0.0.0", port: int = 8090):
    logger.info("=" * 60)
    logger.info("Bayesian-AGI-Core MCP Server v2.0")
    logger.info("=" * 60)
    logger.info(f"服务地址: http://{host}:{port}/mcp")
    logger.info(f"数据目录: {DATA_DIR}")
    logger.info(f"记忆条目: {len(server.memory.items)}")
    logger.info(f"Bug条目: {len(server.bug_db.bugs)}")
    logger.info("=" * 60)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    start_server()
