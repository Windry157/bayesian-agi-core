"""
Bridge Server 代理模块

对接 OpenClaw 生态，提供与 OpenCode CLI Agent (Brother) 的通信能力。
支持 OpenClaw 的标准协议，实现 /ping, /call-brother, /check-notify 等接口。

架构:
    - Bridge Server 代理监听 :19876 端口
    - 与 bayesian-agi-core 的 Agent Core 集成
    - 支持 TF-IDF 语义搜索
    - 支持 Agent 间通信协议
"""

import asyncio
import hashlib
import hmac
import json
import httpx
import logging
import math
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .exceptions import BridgeException, ErrorCode, map_httpx_exception
from .idempotency import IdempotencyChecker, get_idempotency_checker
from .parallel_executor import AsyncParallelExecutor, ParallelResult, TaskResult, TaskStatus

logger = logging.getLogger(__name__)


class BridgeConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 19876
    ollama_url: str = "http://127.0.0.1:11434"
    memory_dir: str = "memory"
    workspace_dir: str = os.getenv("OPENCLAW_WORKSPACE", "openclaw_workspace")
    brother_url: Optional[str] = None


class BridgeServer:
    def __init__(self, config: Optional[BridgeConfig] = None):
        self.config = config or BridgeConfig()
        self.app = FastAPI(title="Bridge Server Proxy")
        self._setup_exception_handlers()
        self._setup_routes()
        self._setup_cors()
        self._idempotency = get_idempotency_checker()

        self._memory_index: List[Dict[str, Any]] = []
        self._last_index_time: float = 0
        self._notify_dir = Path(self.config.workspace_dir) / ".bridge" / "notify"
        self._outbox_dir = Path(self.config.workspace_dir) / ".bridge" / "outbox"
        
        self._executor = AsyncParallelExecutor(max_concurrency=10)
        self._total_call_count = 0
        self._total_parallel_call_count = 0

    def _setup_cors(self):
        from fastapi.middleware.cors import CORSMiddleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _setup_exception_handlers(self):
        """设置统一异常处理器"""

        @self.app.exception_handler(BridgeException)
        async def bridge_exception_handler(request: Request, exc: BridgeException):
            logger.error(f"BridgeException: {exc.to_dict()}")
            return JSONResponse(
                status_code=self._get_http_status(exc.code),
                content=exc.to_dict()
            )

        @self.app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
            from .exceptions import UnknownException
            return JSONResponse(
                status_code=500,
                content=UnknownException(
                    message=f"内部服务器错误: {str(exc)}",
                    cause=exc,
                    context={"path": request.url.path}
                ).to_dict()
            )

    def _get_http_status(self, code: ErrorCode) -> int:
        """将错误码转换为 HTTP 状态码"""
        code_str = code.value[:4]
        if code_str.startswith("2"):
            return 401 if "AUTH" in code.value else 403 if "FORBIDDEN" in code.value else 400
        elif code_str.startswith("3"):
            return 409  # Conflict
        elif code_str.startswith("5"):
            return 503  # Service Unavailable
        return 500

    def _setup_routes(self):
        @self.app.get("/ping")
        async def ping():
            return {"status": "ok", "timestamp": time.time()}

        @self.app.post("/call-brother")
        async def call_brother(request: Request):
            body = await request.json()
            message = body.get("message", "")
            topic = body.get("topic", "")
            multi_agent_urls = body.get("multi_agent_urls", None)
            # 向后兼容：支持 multi_brother_urls 别名
            if multi_agent_urls is None:
                multi_agent_urls = body.get("multi_brother_urls", None)
            
            # 幂等性检查
            idempotency_key = request.headers.get("X-Idempotency-Key")
            if idempotency_key is None:
                idempotency_key = self._idempotency.generate_key("POST", "/call-brother", body)
            
            should_process, cached_result = await self._idempotency.check_and_start(idempotency_key)
            
            if not should_process:
                logger.info(f"Using cached result for idempotency key: {idempotency_key}")
                return cached_result
            
            try:
                result = await self._handle_call_brother(message, topic, multi_agent_urls)
                await self._idempotency.complete(idempotency_key, result)
                return result
            except Exception as e:
                await self._idempotency.fail(idempotency_key, {"error": str(e)})
                raise

        @self.app.get("/check-notify")
        async def check_notify():
            return await self._handle_check_notify()

        @self.app.get("/check-outbox")
        async def check_outbox():
            return await self._handle_check_outbox()

        @self.app.post("/search")
        async def search(request: Request):
            body = await request.json()
            query = body.get("query", "")
            limit = body.get("limit", 5)
            return await self._handle_search(query, limit)

        @self.app.post("/memory/write")
        async def write_memory(request: Request):
            body = await request.json()
            content = body.get("content", "")
            return await self._handle_write_memory(content)

        @self.app.get("/health")
        async def health():
            return {
                "status": "healthy",
                "service": "bayesian-agi-core-bridge",
                "version": "1.0.0",
                "monitoring": {
                    "total_call_count": self._total_call_count,
                    "total_parallel_call_count": self._total_parallel_call_count
                }
            }
            
        @self.app.get("/monitoring")
        async def monitoring():
            return {
                "total_call_count": self._total_call_count,
                "total_parallel_call_count": self._total_parallel_call_count,
                "max_concurrency": self._executor.max_concurrency
            }

    async def _handle_call_brother(
        self, 
        message: str, 
        topic: str, 
        multi_agent_urls: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        处理 /call-brother 请求
        
        Args:
            message: 消息内容
            topic: 消息主题
            multi_agent_urls: 多个 Agent 的 URL 列表（用于并行调用）
            
        Returns:
            结构化的响应结果
        """
        self._total_call_count += 1
        start_time = time.time()
        
        if multi_agent_urls and len(multi_agent_urls) > 0:
            self._total_parallel_call_count += 1
            logger.info(f"Starting parallel call to {len(multi_agent_urls)} agent URLs")
            
            async def call_single_agent(url: str) -> Dict[str, Any]:
                """
                调用单个 Agent
                
                Args:
                    url: Agent URL
                    
                Returns:
                    Agent 响应
                """
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            f"{url}/call-brother",
                            json={"message": message, "topic": topic},
                            timeout=30.0
                        )
                        return response.json()
                except Exception as e:
                    logger.warning(f"Failed to call agent at {url}: {e}")
                    raise e
            
            # 创建任务列表
            tasks = [lambda url=url: call_single_agent(url) for url in multi_agent_urls]
            parallel_result: ParallelResult = await self._executor.execute(tasks)
            
            total_time = time.time() - start_time
            logger.info(f"Parallel call completed in {total_time:.2f}s: {parallel_result.success_count} succeeded, {parallel_result.failed_count} failed")
            
            results: List[Dict[str, Any]] = []
            
            for i, task_result in enumerate(parallel_result.task_results):
                result_dict: Dict[str, Any] = {
                    "url": multi_agent_urls[i],
                    "status": "failed",
                    "result": None,
                    "error": None,
                    "execution_time": 0.0
                }
                
                if isinstance(task_result, TaskResult):
                    if task_result.status == TaskStatus.SUCCESS:
                        result_dict["status"] = "success"
                    else:
                        result_dict["status"] = "failed"
                    
                    result_dict["result"] = task_result.result
                    if task_result.error:
                        result_dict["error"] = str(task_result.error)
                    result_dict["execution_time"] = task_result.execution_time
                elif isinstance(task_result, Exception):
                    result_dict["error"] = str(task_result)
                
                results.append(result_dict)
            
            return {
                "status": "parallel_completed",
                "total_execution_time": total_time,
                "success_count": parallel_result.success_count,
                "failed_count": parallel_result.failed_count,
                "results": results,
                "message": message,
                "topic": topic,
                "timestamp": time.time()
            }
        elif self.config.brother_url:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.config.brother_url}/call-brother",
                        json={"message": message, "topic": topic},
                        timeout=30.0
                    )
                    result = response.json()
                    total_time = time.time() - start_time
                    logger.info(f"Single agent call completed in {total_time:.2f}s")
                    return result
            except Exception as e:
                logger.warning(f"Failed to call agent: {e}")

        return {
            "status": "queued",
            "message": f"Message queued for agent: {message[:50]}...",
            "topic": topic,
            "timestamp": time.time()
        }

    async def _handle_check_notify(self) -> Dict[str, Any]:
        notify_dir = Path(self.config.workspace_dir) / ".bridge" / "notify"
        has_new = False
        messages = []

        if notify_dir.exists():
            for flag_file in notify_dir.glob("*.flag"):
                has_new = True
                messages.append({
                    "file": flag_file.name,
                    "content": flag_file.read_text(encoding="utf-8") if flag_file.stat().st_size > 0 else ""
                })

        return {"hasNew": has_new, "messages": messages}

    async def _handle_check_outbox(self) -> Dict[str, Any]:
        outbox_dir = Path(self.config.workspace_dir) / ".bridge" / "outbox"
        messages = []

        if outbox_dir.exists():
            for msg_file in sorted(outbox_dir.glob("*.json")):
                try:
                    messages.append({
                        "file": msg_file.name,
                        "content": json.loads(msg_file.read_text(encoding="utf-8"))
                    })
                except Exception as e:
                    logger.warning(f"Failed to read outbox message: {e}")

        return {"messages": messages}

    async def _handle_search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        self._ensure_index()
        results = self._tfidf_search(query, limit)
        return {"results": results}

    async def _handle_write_memory(self, content: str) -> Dict[str, Any]:
        memory_dir = Path(self.config.memory_dir)
        memory_dir.mkdir(parents=True, exist_ok=True)

        date_str = datetime.now().strftime("%Y-%m-%d")
        memory_file = memory_dir / f"{date_str}.md"

        timestamp = datetime.now().strftime("%H:%M")
        entry = f"\n## 对话摘要 {timestamp}\n{content}\n"

        with open(memory_file, "a", encoding="utf-8") as f:
            f.write(entry)

        self._invalidate_index()
        return {"status": "ok", "file": str(memory_file)}

    def _ensure_index(self):
        if self._needs_reindex():
            self._build_index()

    def _needs_reindex(self) -> bool:
        if not self._memory_index or time.time() - self._last_index_time > 300:
            return True
        return False

    def _invalidate_index(self):
        self._memory_index = []
        self._last_index_time = 0

    def _build_index(self):
        memory_dir = Path(self.config.memory_dir)
        self._memory_index = []

        if not memory_dir.exists():
            return

        for md_file in memory_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                self._memory_index.append({
                    "id": md_file.stem,
                    "file": str(md_file),
                    "text": content,
                    "mtime": md_file.stat().st_mtime
                })
            except Exception as e:
                logger.warning(f"Failed to index {md_file}: {e}")

        self._last_index_time = time.time()

    def _tfidf_search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        if not self._memory_index:
            return []

        all_docs = [d["text"] for d in self._memory_index]
        idf_map = self._compute_idf(all_docs)

        q_tf = self._compute_term_freq(query)
        q_vec = {t: tf * (idf_map.get(t, 1)) for t, tf in q_tf.items()}

        results = []
        for doc in self._memory_index:
            d_tf = self._compute_term_freq(doc["text"])
            d_vec = {t: tf * (idf_map.get(t, 1)) for t, tf in d_tf.items()}

            score = self._cosine_similarity(q_vec, d_vec)
            results.append({
                "id": doc["id"],
                "file": doc["file"],
                "score": score,
                "snippet": doc["text"][:200]
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r'[\w\u4e00-\u9fff]+', text.lower())

    def _compute_term_freq(self, text: str) -> Dict[str, float]:
        tokens = self._tokenize(text)
        if not tokens:
            return {}
        tf = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        for k in tf:
            tf[k] /= len(tokens)
        return tf

    def _compute_idf(self, docs: List[str]) -> Dict[str, float]:
        n = len(docs)
        df = {}
        for doc in docs:
            seen = set(self._tokenize(doc))
            for t in seen:
                df[t] = df.get(t, 0) + 1

        idf = {}
        for t, df_t in df.items():
            idf[t] = math.log((n + 1) / (df_t + 1)) + 1
        return idf

    def _cosine_similarity(self, a: Dict[str, float], b: Dict[str, float]) -> float:
        keys = set(a.keys()) | set(b.keys())
        dot = sum(a.get(k, 0) * b.get(k, 0) for k in keys)
        na = math.sqrt(sum(a.get(k, 0) ** 2 for k in keys))
        nb = math.sqrt(sum(b.get(k, 0) ** 2 for k in keys))
        if not na or not nb:
            return 0
        return dot / (na * nb)

    def run(self, host: Optional[str] = None, port: Optional[int] = None):
        uvicorn.run(
            self.app,
            host=host or self.config.host,
            port=port or self.config.port,
            log_level="info"
        )


_bridge_instance: Optional[BridgeServer] = None


def get_bridge_server() -> BridgeServer:
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = BridgeServer()
    return _bridge_instance


def create_bridge_server(config: Optional[BridgeConfig] = None) -> BridgeServer:
    global _bridge_instance
    _bridge_instance = BridgeServer(config)
    return _bridge_instance


if __name__ == "__main__":
    server = get_bridge_server()
    server.run()