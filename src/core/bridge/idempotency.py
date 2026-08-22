"""
幂等性检查器

确保关键操作不会因网络重试而被重复执行。

使用方式:
    1. 客户端在请求头中传入 X-Idempotency-Key
    2. 服务端检查该 key 是否已处理
    3. 如果已处理，返回缓存的结果
    4. 如果未处理，执行操作并缓存结果
"""

import hashlib
import json
import logging
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class IdempotencyRecord:
    """幂等性记录"""

    def __init__(
        self,
        key: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        created_at: float = None,
        expires_at: float = None
    ):
        self.key = key
        self.status = status  # "processing", "completed", "failed"
        self.result = result
        self.created_at = created_at or time.time()
        self.expires_at = expires_at or (time.time() + 3600)  # 默认 1 小时

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "status": self.status,
            "result": self.result,
            "created_at": self.created_at,
            "expires_at": self.expires_at
        }


class IdempotencyChecker:
    """
    幂等性检查器

    用于防止因网络重试导致的重复操作。
    基于 LRU 缓存实现，自动过期清理。
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: int = 3600,
        cleanup_interval: int = 300
    ):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        self._cache: OrderedDict[str, IdempotencyRecord] = OrderedDict()
        self._last_cleanup = time.time()

    def generate_key(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> str:
        """
        生成幂等性 key

        基于方法、路径、请求体生成唯一的 key
        """
        content = f"{method}:{path}"
        if body:
            body_str = json.dumps(body, sort_keys=True)
            content += f":{hashlib.md5(body_str.encode()).hexdigest()}"
        if user_id:
            content += f":{user_id}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    async def check_and_start(
        self,
        key: str,
        ttl: Optional[int] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        检查并标记为处理中

        Returns:
            (should_process, cached_result)
            - should_process=True, cached_result=None: 需要执行操作
            - should_process=False, cached_result={...}: 返回缓存结果
        """
        self._maybe_cleanup()

        now = time.time()
        expires_at = now + (ttl or self.default_ttl)

        if key in self._cache:
            record = self._cache[key]

            if record.status == "processing":
                if record.is_expired():
                    record.status = "failed"
                    record.result = {"error": "Previous request expired"}
                else:
                    return False, {"status": "processing", "key": key}

            elif record.status == "completed":
                self._cache.move_to_end(key)
                return False, record.result

            elif record.status == "failed":
                self._cache.move_to_end(key)
                return False, record.result

        record = IdempotencyRecord(
            key=key,
            status="processing",
            created_at=now,
            expires_at=expires_at
        )
        self._cache[key] = record
        self._enforce_size_limit()

        return True, None

    async def complete(
        self,
        key: str,
        result: Dict[str, Any]
    ):
        """标记为完成"""
        if key in self._cache:
            self._cache[key].status = "completed"
            self._cache[key].result = result
            self._cache.move_to_end(key)
            logger.info(f"Idempotency check passed: {key}")

    async def fail(
        self,
        key: str,
        error: Dict[str, Any]
    ):
        """标记为失败"""
        if key in self._cache:
            self._cache[key].status = "failed"
            self._cache[key].result = {"error": error}
            self._cache.move_to_end(key)
            logger.warning(f"Idempotency check failed: {key}")

    async def clear(self, key: str):
        """清除记录"""
        if key in self._cache:
            del self._cache[key]

    def _maybe_cleanup(self):
        """定期清理过期记录"""
        now = time.time()
        if now - self._last_cleanup < self.cleanup_interval:
            return

        expired_keys = [
            k for k, v in self._cache.items()
            if v.is_expired()
        ]
        for k in expired_keys:
            del self._cache[k]

        self._last_cleanup = now
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired idempotency records")

    def _enforce_size_limit(self):
        """强制大小限制"""
        while len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "total": len(self._cache),
            "max_size": self.max_size,
            "processing": sum(1 for r in self._cache.values() if r.status == "processing"),
            "completed": sum(1 for r in self._cache.values() if r.status == "completed"),
            "failed": sum(1 for r in self._cache.values() if r.status == "failed"),
        }
        return stats


# 全局单例
_idempotency_checker: Optional[IdempotencyChecker] = None


def get_idempotency_checker() -> IdempotencyChecker:
    global _idempotency_checker
    if _idempotency_checker is None:
        _idempotency_checker = IdempotencyChecker()
    return _idempotency_checker
