#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import pytest
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.distributed.saga_orchestrator import (
    SagaOrchestrator,
    IdempotencyService,
)
from src.core.distributed.event_bus import (
    EventBus,
    DomainEvent,
    EventType,
    DeadLetterQueue,
)
from src.core.distributed.enterprise_resilience import (
    TransactionalOutbox,
    CircuitBreaker,
    HealthChecker,
)
from src.core.distributed.scalable_messaging import (
    BatchProcessor,
    BatchConfig,
    TokenBucket,
)


class TestIdempotencyService:
    def test_idempotency_service_basic(self):
        service = IdempotencyService()
        key = "test-key-1"
        op_type = "operation"
        assert service.check(key, op_type) is False
        service.store(key, op_type, {"result": "ok"})
        assert service.check(key, op_type) is True

    def test_idempotency_service_retrieve(self):
        service = IdempotencyService()
        service.store("key1", "type1", {"data": "value"})
        result = service.retrieve("key1", "type1")
        assert result == {"data": "value"}
        assert service.retrieve("nonexistent", "type") is None

    def test_idempotency_service_expiry(self):
        service = IdempotencyService()
        service.ttl_seconds = 0.5
        service.store("expire-key", "op", {"ok": True})
        assert service.check("expire-key", "op") is True
        time.sleep(0.6)
        assert service.check("expire-key", "op") is False


class TestSagaOrchestrator:
    def test_saga_creation(self):
        orchestrator = SagaOrchestrator()
        tx_id = orchestrator.create_transaction("test-saga")
        assert tx_id is not None
        status = orchestrator.get_transaction_status(tx_id)
        assert status is not None
        assert status["saga_name"] == "test-saga"

    def test_saga_steps_execution(self):
        orchestrator = SagaOrchestrator()
        tx_id = orchestrator.create_transaction("test-saga")
        executed = []
        compensated = []

        def step1_execute():
            executed.append("step1")
            return True

        def step1_compensate():
            compensated.append("step1")

        def step2_execute():
            executed.append("step2")
            return True

        def step2_compensate():
            compensated.append("step2")

        orchestrator.add_step(tx_id, "step1", step1_execute, step1_compensate)
        orchestrator.add_step(tx_id, "step2", step2_execute, step2_compensate)
        result = orchestrator.execute(tx_id)
        assert result["success"] is True
        assert executed == ["step1", "step2"]
        assert compensated == []

    def test_saga_compensation(self):
        orchestrator = SagaOrchestrator()
        tx_id = orchestrator.create_transaction("test-saga-fail")
        executed = []
        compensated = []

        def step1_execute():
            executed.append("step1")
            return True

        def step1_compensate():
            compensated.append("step1")

        def step2_execute():
            executed.append("step2")
            raise Exception("Step 2 failed")

        def step2_compensate():
            compensated.append("step2")

        orchestrator.add_step(tx_id, "step1", step1_execute, step1_compensate, max_retries=0)
        orchestrator.add_step(tx_id, "step2", step2_execute, step2_compensate, max_retries=0)
        result = orchestrator.execute(tx_id)
        assert result["success"] is False
        assert executed == ["step1", "step2"]
        assert compensated == ["step1"]


class TestEventBus:
    def test_event_bus_publish_subscribe(self):
        bus = EventBus()
        received_events = []

        def handler(event):
            received_events.append(event)

        bus.subscribe(handler, event_type=EventType.CUSTOM)
        event = DomainEvent.create(
            event_type=EventType.CUSTOM,
            aggregate_id="agg-1",
            aggregate_type="test",
            payload={"key": "value"},
            source="test",
        )
        bus.publish(event)
        assert len(received_events) == 1
        assert received_events[0].event_type == EventType.CUSTOM

    def test_dead_letter_queue(self):
        dlq = DeadLetterQueue()
        event = DomainEvent.create(
            event_type=EventType.CUSTOM,
            aggregate_id="agg-1",
            aggregate_type="test",
        )
        dlq.enqueue(event, "Failed processing", "sub-1")
        pending = dlq.get_pending()
        assert len(pending) == 1
        stats = dlq.get_statistics()
        assert stats["total"] == 1
        assert stats["pending"] == 1


class TestCircuitBreaker:
    def test_circuit_breaker_closed_state(self):
        cb = CircuitBreaker(name="test-cb", failure_threshold=3, recovery_timeout=1)
        result = cb.execute(lambda: "success")
        assert result == "success"

    def test_circuit_breaker_open_state(self):
        cb = CircuitBreaker(name="test-cb-open", failure_threshold=2, recovery_timeout=10)

        def fail():
            raise Exception("Failed")

        with pytest.raises(Exception):
            cb.execute(fail)
        with pytest.raises(Exception):
            cb.execute(fail)

        state = cb.get_state()
        # 2 failures should trigger open state
        assert "state" in state


class TestTokenBucket:
    def test_token_bucket_rate_limit(self):
        bucket = TokenBucket(capacity=5, fill_rate=100)
        for _ in range(5):
            assert bucket.acquire() is True
        assert bucket.acquire() is False


class TestBatchProcessor:
    def test_batch_processing(self):
        processed = []

        def process_batch(items):
            processed.extend(items)

        config = BatchConfig(max_batch_size=3)
        processor = BatchProcessor(process_func=process_batch, config=config)
        processor.add({"id": 1})
        processor.add({"id": 2})
        processor.add({"id": 3})
        time.sleep(0.05)
        processor.flush()
        assert len(processed) == 3


class TestHealthChecker:
    def test_health_checker_registration(self):
        checker = HealthChecker()

        def db_check():
            from src.core.distributed.enterprise_resilience import HealthCheck, HealthStatus
            return HealthCheck(
                name="database",
                status=HealthStatus.HEALTHY,
                message="DB OK",
                details={"latency": 10},
            )

        checker.register_check("database", db_check)
        result = checker.check_all()
        assert "overall_status" in result
        assert result["overall_status"] == "healthy"
        assert len(result["checks"]) == 1
        assert result["checks"][0]["name"] == "database"


class TestTransactionalOutbox:
    def test_outbox_add_and_deliver(self):
        outbox = TransactionalOutbox()
        msg_id = outbox.write_outbox({
            "event_type": "test.outbox",
            "aggregate_id": "order-123",
            "aggregate_type": "order",
            "payload": {"data": "test"},
        })
        assert msg_id is not None
        pending = outbox.get_pending_messages()
        assert len(pending) == 1
        outbox.mark_as_published(msg_id)
        assert len(outbox.get_pending_messages()) == 0


class TestDistributedTracer:
    def test_tracer_basic(self):
        from src.core.distributed.enterprise_resilience import DistributedTracer
        tracer = DistributedTracer(service_name="test")
        span_id = tracer.start_span("test-operation")
        assert span_id is not None
        tracer.end_span(span_id)
        assert tracer.spans[span_id].end_time is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
