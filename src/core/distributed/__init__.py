#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Distributed Systems - 分布式系统组件
包含 Saga 编排、事件驱动架构、幂等性、消息队列、企业级韧性组件等
"""

from .saga_orchestrator import (
    SagaOrchestrator,
    SagaState,
    StepState,
    SagaTransaction,
    SagaStep,
    IdempotencyService
)

from .event_bus import (
    EventBus,
    DomainEvent,
    EventType,
    EventSubscription,
    DeadLetterQueue,
    AggregateRoot
)

from .enterprise_resilience import (
    TransactionalOutbox,
    OutboxMessage,
    OutboxRelay,
    CircuitBreaker,
    CircuitState,
    CircuitBreakerError,
    RateLimiter,
    DistributedTracer,
    Span,
    traced,
    HealthChecker,
    HealthCheck,
    HealthStatus,
    DatabaseHealthCheck,
    EventBusHealthCheck
)

from .scalable_messaging import (
    PartitionedMessageQueue,
    MessageQueuePartition,
    Partitioner,
    PartitionStrategy,
    BatchProcessor,
    BatchConfig,
    TokenBucket,
    LeakyBucket,
    MessageSerializer,
    EnterpriseMessageQueue
)

__all__ = [
    # Saga Orchestration
    "SagaOrchestrator",
    "SagaState",
    "StepState",
    "SagaTransaction",
    "SagaStep",
    "IdempotencyService",
    
    # Event-Driven Architecture
    "EventBus",
    "DomainEvent",
    "EventType",
    "EventSubscription",
    "DeadLetterQueue",
    "AggregateRoot",
    
    # Enterprise Resilience
    "TransactionalOutbox",
    "OutboxMessage",
    "OutboxRelay",
    "CircuitBreaker",
    "CircuitState",
    "CircuitBreakerError",
    "RateLimiter",
    "DistributedTracer",
    "Span",
    "traced",
    "HealthChecker",
    "HealthCheck",
    "HealthStatus",
    "DatabaseHealthCheck",
    "EventBusHealthCheck",
    
    # Scalable Messaging
    "PartitionedMessageQueue",
    "MessageQueuePartition",
    "Partitioner",
    "PartitionStrategy",
    "BatchProcessor",
    "BatchConfig",
    "TokenBucket",
    "LeakyBucket",
    "MessageSerializer",
    "EnterpriseMessageQueue"
]
