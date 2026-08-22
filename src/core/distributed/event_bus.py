#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Event Bus - 事件驱动架构核心组件
实现领域事件、事件订阅/发布、消息队列、死信队列
"""
import uuid
import time
import json
import logging
from typing import Dict, List, Optional, Any, Callable, Type, TypeVar
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from datetime import datetime
from collections import defaultdict, deque
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

T = TypeVar('T', bound='DomainEvent')


class EventType(Enum):
    """事件类型枚举"""
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    ORDER_CREATED = "order_created"
    ORDER_UPDATED = "order_updated"
    MEMORY_ADDED = "memory_added"
    MEMORY_UPDATED = "memory_updated"
    COGNITION_COMPLETED = "cognition_completed"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    NOTIFICATION_SENT = "notification_sent"
    CUSTOM = "custom"


@dataclass
class DomainEvent:
    """领域事件基类"""
    event_id: str
    event_type: EventType
    aggregate_id: str  # 聚合根 ID
    aggregate_type: str  # 聚合根类型
    occurred_at: str
    version: int = 1
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    
    @classmethod
    def create(cls, event_type: EventType, aggregate_id: str,
               aggregate_type: str, payload: Optional[Dict] = None,
               source: str = "", metadata: Optional[Dict] = None) -> 'DomainEvent':
        """创建一个新的领域事件"""
        return cls(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            occurred_at=datetime.now().isoformat(),
            payload=payload or {},
            source=source,
            metadata=metadata or {}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "occurred_at": self.occurred_at,
            "version": self.version,
            "payload": self.payload,
            "metadata": self.metadata,
            "source": self.source
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DomainEvent':
        """从字典反序列化"""
        data = data.copy()
        if isinstance(data.get("event_type"), str):
            data["event_type"] = EventType(data["event_type"])
        return cls(**data)
    
    def to_json(self) -> str:
        """序列化为 JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class EventSubscription:
    """事件订阅"""
    subscription_id: str
    event_type: Optional[EventType]
    handler: Callable[[DomainEvent], None]
    filter_fn: Optional[Callable[[DomainEvent], bool]] = None
    retry_policy: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True


class EventBus:
    """事件总线 - 领域事件发布/订阅核心"""
    
    def __init__(self, idempotency_service: Optional['IdempotencyService'] = None):
        from .saga_orchestrator import IdempotencyService
        self.subscribers: Dict[Optional[EventType], List[EventSubscription]] = defaultdict(list)
        self.event_log: List[DomainEvent] = []
        self.idempotency = idempotency_service or IdempotencyService()
        self.dlq: 'DeadLetterQueue' = DeadLetterQueue()
        self._in_memory_queue: deque = deque()
        self._is_processing: bool = False
    
    def publish(self, event: DomainEvent) -> bool:
        """
        发布领域事件
        
        Args:
            event: 领域事件
            
        Returns:
            是否成功发布
        """
        # 幂等性检查
        if self.idempotency.check(event.event_id, "event_published"):
            logger.info(f"Event {event.event_id} already published (idempotent)")
            return True
        
        logger.info(f"Publishing event: {event.event_type.value} ({event.event_id})")
        self.event_log.append(event)
        self._in_memory_queue.append(event)
        self.idempotency.store(event.event_id, "event_published", {"success": True})
        
        # 立即处理（异步队列会在生产环境使用）
        self._process_event(event)
        
        return True
    
    def publish_batch(self, events: List[DomainEvent]) -> int:
        """批量发布事件"""
        success_count = 0
        for event in events:
            if self.publish(event):
                success_count += 1
        return success_count
    
    def subscribe(self, handler: Callable[[DomainEvent], None],
                  event_type: Optional[EventType] = None,
                  filter_fn: Optional[Callable[[DomainEvent], bool]] = None,
                  retry_policy: Optional[Dict] = None) -> str:
        """
        订阅事件
        
        Args:
            handler: 事件处理函数
            event_type: 过滤的事件类型（None 表示订阅所有）
            filter_fn: 额外的过滤函数
            retry_policy: 重试策略
            
        Returns:
            subscription_id: 订阅 ID
        """
        subscription = EventSubscription(
            subscription_id=str(uuid.uuid4()),
            event_type=event_type,
            handler=handler,
            filter_fn=filter_fn,
            retry_policy=retry_policy or {
                "max_retries": 3,
                "backoff_seconds": 0.1,
                "exponential_backoff": True
            }
        )
        
        self.subscribers[event_type].append(subscription)
        logger.info(f"Subscribed handler {handler.__name__} to {event_type or 'all events'}")
        
        return subscription.subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """取消订阅"""
        for event_type, subs in self.subscribers.items():
            for i, sub in enumerate(subs):
                if sub.subscription_id == subscription_id:
                    subs.pop(i)
                    logger.info(f"Unsubscribed {subscription_id}")
                    return True
        return False
    
    def _process_event(self, event: DomainEvent) -> None:
        """处理单个事件（调用所有相关订阅者）"""
        # 获取所有匹配的订阅者
        matching_subscribers = []
        if None in self.subscribers:
            matching_subscribers.extend(self.subscribers[None])
        if event.event_type in self.subscribers:
            matching_subscribers.extend(self.subscribers[event.event_type])
        
        for subscription in matching_subscribers:
            if not subscription.is_active:
                continue
            
            # 应用过滤函数
            if subscription.filter_fn and not subscription.filter_fn(event):
                continue
            
            # 执行处理（含重试）
            self._execute_handler_with_retry(subscription, event)
    
    def _execute_handler_with_retry(self, subscription: EventSubscription,
                                     event: DomainEvent) -> None:
        """执行处理器，含重试逻辑"""
        max_retries = subscription.retry_policy.get("max_retries", 3)
        backoff = subscription.retry_policy.get("backoff_seconds", 0.1)
        exponential = subscription.retry_policy.get("exponential_backoff", True)
        
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                subscription.handler(event)
                logger.debug(f"Handler processed event {event.event_id} successfully")
                return
                
            except Exception as e:
                last_error = e
                logger.warning(f"Handler failed attempt {attempt + 1}/{max_retries}: {str(e)}")
                
                if attempt < max_retries:
                    wait_time = backoff * (2 ** attempt) if exponential else backoff
                    time.sleep(wait_time)
        
        # 所有重试失败，发送到死信队列
        logger.error(f"Handler failed permanently, sending to DLQ: {event.event_id}")
        self.dlq.enqueue(event, str(last_error), subscription.subscription_id)


class DeadLetterQueue:
    """死信队列 - 处理失败的消息"""
    
    def __init__(self):
        self.queue: List[Dict[str, Any]] = []
        self.analysis_rules: List[Callable] = []
        self.alert_handlers: List[Callable] = []
    
    def enqueue(self, event: DomainEvent, error_message: str,
                subscription_id: str) -> str:
        """
        将失败的事件入队
        
        Args:
            event: 失败的事件
            error_message: 错误信息
            subscription_id: 订阅 ID
            
        Returns:
            dlq_id: 死信队列 ID
        """
        dlq_id = str(uuid.uuid4())
        entry = {
            "dlq_id": dlq_id,
            "event": event.to_dict(),
            "error": error_message,
            "subscription_id": subscription_id,
            "enqueued_at": datetime.now().isoformat(),
            "status": "pending",
            "analysis_result": None,
            "retry_count": 0,
            "max_retries": 5
        }
        
        self.queue.append(entry)
        logger.error(f"Event {event.event_id} enqueued to DLQ: {error_message}")
        
        # 触发分析和告警
        self._analyze_and_alert(entry)
        
        return dlq_id
    
    def requeue(self, dlq_id: str) -> Optional[DomainEvent]:
        """
        重新入队
        
        Args:
            dlq_id: 死信队列 ID
            
        Returns:
            恢复的事件，或 None
        """
        for entry in self.queue:
            if entry["dlq_id"] == dlq_id and entry["status"] == "pending":
                entry["status"] = "requeued"
                entry["retry_count"] += 1
                
                logger.info(f"Requeued DLQ entry {dlq_id}")
                return DomainEvent.from_dict(entry["event"])
        
        return None
    
    def mark_failed(self, dlq_id: str, reason: str) -> bool:
        """标记为永久失败（需要人工介入）"""
        for entry in self.queue:
            if entry["dlq_id"] == dlq_id:
                entry["status"] = "permanently_failed"
                entry["failure_reason"] = reason
                
                logger.critical(f"DLQ entry {dlq_id} marked as permanently failed: {reason}")
                return True
        return False
    
    def get_pending(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取待处理的死信"""
        return [e for e in self.queue if e["status"] == "pending"][:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取死信队列统计"""
        stats = {
            "total": len(self.queue),
            "pending": sum(1 for e in self.queue if e["status"] == "pending"),
            "requeued": sum(1 for e in self.queue if e["status"] == "requeued"),
            "permanently_failed": sum(1 for e in self.queue if e["status"] == "permanently_failed"),
            "by_event_type": defaultdict(int),
            "by_error_type": defaultdict(int)
        }
        
        for entry in self.queue:
            event_type = entry["event"]["event_type"]
            stats["by_event_type"][event_type] += 1
            
            error_type = entry["error"].split(":")[0]
            stats["by_error_type"][error_type] += 1
        
        return dict(stats)
    
    def add_analysis_rule(self, rule: Callable) -> None:
        """添加分析规则"""
        self.analysis_rules.append(rule)
    
    def add_alert_handler(self, handler: Callable) -> None:
        """添加告警处理器"""
        self.alert_handlers.append(handler)
    
    def _analyze_and_alert(self, entry: Dict[str, Any]) -> None:
        """分析失败原因并触发告警"""
        # 执行分析规则
        analysis_result = None
        for rule in self.analysis_rules:
            try:
                result = rule(entry)
                if result:
                    analysis_result = result
                    entry["analysis_result"] = result
                    break
            except Exception as e:
                logger.error(f"Analysis rule failed: {str(e)}")
        
        # 确定告警级别
        alert_level = self._determine_alert_level(entry, analysis_result)
        
        # 触发告警
        for handler in self.alert_handlers:
            try:
                handler(entry, alert_level, analysis_result)
            except Exception as e:
                logger.error(f"Alert handler failed: {str(e)}")
    
    def _determine_alert_level(self, entry: Dict[str, Any],
                                analysis_result: Optional[str]) -> str:
        """确定告警级别"""
        if analysis_result and "CRITICAL" in analysis_result:
            return "CRITICAL"
        
        if "database" in entry["error"].lower() or "timeout" in entry["error"].lower():
            return "ERROR"
        
        return "WARNING"
    
    def cleanup_old_entries(self, max_age_seconds: int = 86400 * 7) -> int:
        """清理旧的条目（默认7天）"""
        cutoff = time.time() - max_age_seconds
        removed = 0
        
        new_queue = []
        for entry in self.queue:
            try:
                enqueued_time = datetime.fromisoformat(entry["enqueued_at"])
                if enqueued_time.timestamp() < cutoff and entry["status"] != "pending":
                    removed += 1
                else:
                    new_queue.append(entry)
            except Exception:
                new_queue.append(entry)
        
        self.queue = new_queue
        logger.info(f"Cleaned up {removed} old DLQ entries")
        return removed


class AggregateRoot(ABC):
    """聚合根基类 - DDD 模式"""
    
    def __init__(self, aggregate_id: str, aggregate_type: str):
        self.aggregate_id = aggregate_id
        self.aggregate_type = aggregate_type
        self.version: int = 0
        self._pending_events: List[DomainEvent] = []
        self._created_at: str = datetime.now().isoformat()
        self._updated_at: str = self._created_at
    
    def _raise_event(self, event_type: EventType, payload: Dict[str, Any],
                     source: str = "", metadata: Optional[Dict] = None) -> None:
        """引发领域事件（内部方法）"""
        event = DomainEvent.create(
            event_type=event_type,
            aggregate_id=self.aggregate_id,
            aggregate_type=self.aggregate_type,
            payload=payload,
            source=source,
            metadata=metadata
        )
        self._pending_events.append(event)
        logger.debug(f"Raised event: {event_type.value}")
    
    def get_pending_events(self) -> List[DomainEvent]:
        """获取待发布的事件"""
        return self._pending_events.copy()
    
    def clear_pending_events(self) -> None:
        """清空待发布事件"""
        self._pending_events.clear()
    
    def mark_events_as_published(self) -> None:
        """标记事件为已发布（通常在成功发布后调用）"""
        self.version += 1
        self._updated_at = datetime.now().isoformat()
        self.clear_pending_events()
    
    @abstractmethod
    def apply(self, event: DomainEvent) -> None:
        """应用事件（事件溯源模式）"""
        pass
