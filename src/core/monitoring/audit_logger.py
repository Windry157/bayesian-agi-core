#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
审计日志系统
记录关键操作和安全事件
"""
from typing import Callable
import time
import json
import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """审计事件类型"""
    # 用户操作
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_REGISTER = "user_register"
    
    # 资源访问
    RESOURCE_ACCESS = "resource_access"
    RESOURCE_CREATE = "resource_create"
    RESOURCE_UPDATE = "resource_update"
    RESOURCE_DELETE = "resource_delete"
    
    # 系统操作
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    CONFIG_CHANGE = "config_change"
    
    # 安全事件
    AUTHENTICATION_SUCCESS = "auth_success"
    AUTHENTICATION_FAILURE = "auth_failure"
    AUTHORIZATION_DENIED = "authorization_denied"
    SECURITY_ALERT = "security_alert"
    
    # 数据操作
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"
    DATA_QUERY = "data_query"
    
    # API操作
    API_CALL = "api_call"
    API_ERROR = "api_error"


class AuditLevel(Enum):
    """审计级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """审计事件"""
    event_id: str
    event_type: str
    event_level: str
    timestamp: float
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    tenant_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action: Optional[str] = None
    status: str = "success"
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    duration: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "event_level": self.event_level,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "user_id": self.user_id,
            "user_name": self.user_name,
            "tenant_id": self.tenant_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "status": self.status,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_id": self.request_id,
            "duration": self.duration,
            "metadata": self.metadata,
            "error_message": self.error_message
        }


class AuditLogger:
    """
    审计日志记录器
    
    功能:
    - 记录关键操作
    - 异步日志处理
    - 多输出支持(文件、数据库、外部API)
    - 日志查询和过滤
    """
    
    def __init__(
        self,
        log_file: Optional[str] = None,
        max_events_in_memory: int = 10000,
        enable_async: bool = True,
        flush_interval: float = 5.0
    ):
        """
        初始化审计日志记录器
        
        Args:
            log_file: 日志文件路径
            max_events_in_memory: 内存中保留的最大事件数
            enable_async: 是否启用异步处理
            flush_interval: 刷新间隔(秒)
        """
        self.log_file = log_file
        self.max_events_in_memory = max_events_in_memory
        self.enable_async = enable_async
        self.flush_interval = flush_interval
        
        # 内存存储
        self._events: List[AuditEvent] = []
        self._pending_events: List[AuditEvent] = []
        
        # 事件队列
        self._queue: asyncio.Queue = asyncio.Queue() if enable_async else None
        
        # 锁
        self._lock = asyncio.Lock() if enable_async else None
        
        # 后台任务
        self._processor_task: Optional[asyncio.Task] = None
        self._running = False
        
        # 输出处理器
        self._output_handlers: List[Callable[[AuditEvent], None]] = []
        
        # 如果配置了文件输出，添加文件处理器
        if log_file:
            self._output_handlers.append(self._file_output_handler)
    
    async def start(self):
        """启动审计日志系统"""
        if self._running:
            return
        
        self._running = True
        logger.info("🚀 审计日志系统启动")
        
        if self.enable_async:
            self._processor_task = asyncio.create_task(self._process_events())
    
    async def stop(self):
        """停止审计日志系统"""
        self._running = False
        
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        
        # 刷新剩余事件
        await self._flush_events()
        logger.info("👋 审计日志系统停止")
    
    async def log_event(
        self,
        event_type: Union[AuditEventType, str],
        event_level: Union[AuditLevel, str] = AuditLevel.INFO,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        tenant_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[str] = None,
        status: str = "success",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        duration: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> str:
        """
        记录审计事件
        
        Args:
            event_type: 事件类型
            event_level: 事件级别
            user_id: 用户ID
            user_name: 用户名
            tenant_id: 租户ID
            resource_type: 资源类型
            resource_id: 资源ID
            action: 操作描述
            status: 状态(success/failure)
            ip_address: IP地址
            user_agent: 用户代理
            request_id: 请求ID
            duration: 耗时(秒)
            metadata: 附加元数据
            error_message: 错误信息
            
        Returns:
            事件ID
        """
        event_id = self._generate_event_id()
        
        event = AuditEvent(
            event_id=event_id,
            event_type=event_type.value if isinstance(event_type, AuditEventType) else event_type,
            event_level=event_level.value if isinstance(event_level, AuditLevel) else event_level,
            timestamp=time.time(),
            user_id=user_id,
            user_name=user_name,
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            status=status,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            duration=duration,
            metadata=metadata or {},
            error_message=error_message
        )
        
        if self.enable_async and self._running and self._processor_task:
            await self._queue.put(event)
        else:
            # 异步处理管线未启动时直接同步处理，避免事件静默滞留队列
            await self._process_single_event(event)
        
        return event_id
    
    async def _process_events(self):
        """后台处理事件"""
        while self._running:
            try:
                # 从队列获取事件
                try:
                    event = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=self.flush_interval
                    )
                    await self._process_single_event(event)
                    self._queue.task_done()
                except asyncio.TimeoutError:
                    # 超时刷新
                    await self._flush_events()
            except Exception as e:
                logger.error(f"❌ 处理审计事件时出错: {e}")
    
    async def _process_single_event(self, event: AuditEvent):
        """处理单个事件"""
        async with self._lock:
            # 添加到内存
            self._events.append(event)
            self._pending_events.append(event)
            
            # 限制内存大小
            if len(self._events) > self.max_events_in_memory:
                self._events = self._events[-self.max_events_in_memory:]
            
            # 调用输出处理器
            for handler in self._output_handlers:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"❌ 审计日志输出处理器错误: {e}")
    
    async def _flush_events(self):
        """刷新待处理事件"""
        # 这里可以实现批量写入数据库等操作
        self._pending_events.clear()
    
    def _file_output_handler(self, event: AuditEvent):
        """文件输出处理器"""
        if self.log_file:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(event.to_dict(), ensure_ascii=False) + '\n')
            except Exception as e:
                logger.error(f"❌ 写入审计日志文件失败: {e}")
    
    def add_output_handler(self, handler: Callable[[AuditEvent], None]):
        """添加自定义输出处理器"""
        self._output_handlers.append(handler)
    
    def query_events(
        self,
        event_type: Optional[str] = None,
        event_level: Optional[str] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        查询审计事件
        
        Args:
            event_type: 事件类型过滤
            event_level: 事件级别过滤
            user_id: 用户ID过滤
            tenant_id: 租户ID过滤
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量限制
            
        Returns:
            事件列表
        """
        filtered = self._events
        
        if event_type:
            filtered = [e for e in filtered if e.event_type == event_type]
        if event_level:
            filtered = [e for e in filtered if e.event_level == event_level]
        if user_id:
            filtered = [e for e in filtered if e.user_id == user_id]
        if tenant_id:
            filtered = [e for e in filtered if e.tenant_id == tenant_id]
        if start_time:
            filtered = [e for e in filtered if e.timestamp >= start_time]
        if end_time:
            filtered = [e for e in filtered if e.timestamp <= end_time]
        
        # 按时间倒序
        filtered.sort(key=lambda x: x.timestamp, reverse=True)
        
        return [e.to_dict() for e in filtered[:limit]]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取审计日志统计"""
        now = time.time()
        last_hour = now - 3600
        last_day = now - 86400
        
        stats = {
            'total_events': len(self._events),
            'events_last_hour': sum(1 for e in self._events if e.timestamp >= last_hour),
            'events_last_day': sum(1 for e in self._events if e.timestamp >= last_day),
            'by_level': {},
            'by_type': {}
        }
        
        # 按级别统计
        for event in self._events:
            stats['by_level'][event.event_level] = stats['by_level'].get(event.event_level, 0) + 1
            stats['by_type'][event.event_type] = stats['by_type'].get(event.event_type, 0) + 1
        
        return stats
    
    def _generate_event_id(self) -> str:
        """生成唯一事件ID"""
        timestamp = str(time.time()).encode()
        random_data = str(id(self)).encode()
        return hashlib.sha256(timestamp + random_data).hexdigest()[:16]


# 全局审计日志实例
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger(
    log_file: Optional[str] = "audit.log",
    **kwargs
) -> AuditLogger:
    """获取或创建全局审计日志记录器"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger(log_file=log_file, **kwargs)
    return _audit_logger


def audit(
    event_type: Union[AuditEventType, str],
    event_level: Union[AuditLevel, str] = AuditLevel.INFO,
    **event_kwargs
):
    """
    审计日志装饰器
    
    Args:
        event_type: 事件类型
        event_level: 事件级别
        **event_kwargs: 其他事件参数
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            audit_logger = get_audit_logger()
            start_time = time.time()
            status = "success"
            error_msg = None
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "failure"
                error_msg = str(e)
                raise
            finally:
                duration = time.time() - start_time
                await audit_logger.log_event(
                    event_type=event_type,
                    event_level=event_level,
                    status=status,
                    duration=duration,
                    error_message=error_msg,
                    metadata={'function': func.__name__},
                    **event_kwargs
                )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            audit_logger = get_audit_logger()
            start_time = time.time()
            status = "success"
            error_msg = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = "failure"
                error_msg = str(e)
                raise
            finally:
                duration = time.time() - start_time
                loop = asyncio.get_event_loop()
                loop.run_until_complete(audit_logger.log_event(
                    event_type=event_type,
                    event_level=event_level,
                    status=status,
                    duration=duration,
                    error_message=error_msg,
                    metadata={'function': func.__name__},
                    **event_kwargs
                ))
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
