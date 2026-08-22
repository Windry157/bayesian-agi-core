"""
轻量级任务分发器
支持 asyncio.Queue 进程内队列和 Redis 后端
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Awaitable

logger = logging.getLogger(__name__)


class TaskDispatcher:
    def __init__(self, num_workers: int = 2, redis_url: Optional[str] = None):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.workers: List[asyncio.Task] = []
        self._num_workers = num_workers
        self._redis_url = redis_url
        self._pubsub_task: Optional[asyncio.Task] = None
        self._redis = None
        self._running = False

    async def start(self):
        self._running = True
        for _ in range(self._num_workers):
            worker = asyncio.create_task(self._worker_loop())
            self.workers.append(worker)
        if self._redis_url:
            try:
                import redis.asyncio as aioredis
                self._redis = aioredis.from_url(self._redis_url)
                self._pubsub_task = asyncio.create_task(self._redis_subscriber())
                logger.info(f"TaskDispatcher: Redis backend connected ({self._redis_url})")
            except Exception as e:
                logger.warning(f"TaskDispatcher: Redis unavailable, using in-process queue only ({e})")
        logger.info(f"TaskDispatcher: started {self._num_workers} workers")

    async def stop(self):
        self._running = False
        for _ in self.workers:
            await self.queue.put(None)
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
        if self._pubsub_task:
            self._pubsub_task.cancel()
        if self._redis:
            await self._redis.aclose()

    async def submit(self, task_type: str, payload: Optional[Dict[str, Any]] = None):
        task = {"type": task_type, "payload": payload or {}}
        await self.queue.put(task)
        if self._redis:
            try:
                await self._redis.publish("task:dispatch", json.dumps(task))
            except Exception:
                pass

    async def _worker_loop(self):
        while self._running:
            task = await self.queue.get()
            if task is None:
                break
            try:
                await self._execute(task)
            except Exception as e:
                logger.error(f"Task failed: {task.get('type')} - {e}")
            finally:
                self.queue.task_done()

    async def _redis_subscriber(self):
        try:
            pubsub = self._redis.pubsub()
            await pubsub.subscribe("task:dispatch")
            async for message in pubsub.listen():
                if message["type"] == "message" and self._running:
                    task = json.loads(message["data"])
                    await self.queue.put(task)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning(f"TaskDispatcher: Redis subscriber stopped ({e})")

    async def _execute(self, task: Dict[str, Any]):
        task_type = task.get("type")
        payload = task.get("payload", {})
        if task_type == "flush_memory":
            store = payload.get("store")
            if store:
                await asyncio.to_thread(store._save_sync)
        elif task_type == "flush_bugs":
            db = payload.get("db")
            if db:
                await asyncio.to_thread(db._save_sync)
        elif task_type == "rebuild_index":
            index = payload.get("index")
            if index:
                await asyncio.to_thread(index._rebuild_index)
        elif task_type == "optimize_memory":
            store = payload.get("store")
            action = payload.get("action")
            criteria = payload.get("criteria")
            if store:
                await asyncio.to_thread(store.optimize, action, criteria)
        elif task_type == "custom":
            fn = payload.get("fn")
            if fn:
                result = fn()
                if isinstance(result, Awaitable):
                    await result
        else:
            logger.warning(f"Unknown task type: {task_type}")

    async def flush_all(self, memory_store, bug_db):
        if memory_store:
            await asyncio.to_thread(memory_store._save_sync)
        if bug_db:
            await asyncio.to_thread(bug_db._save_sync)
