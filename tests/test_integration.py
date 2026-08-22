#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import pytest
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.assistant import Assistant
from src.core.distributed.saga_orchestrator import SagaOrchestrator
from src.core.distributed.event_bus import EventBus, DomainEvent, EventType
from src.core.distributed.enterprise_resilience import (
    CircuitBreaker,
    HealthChecker,
    HealthCheck,
    HealthStatus,
)
from src.core.cognition.advanced_reasoning_coordinator import (
    AdvancedReasoningCoordinator,
    ReasoningStrategy,
)
from src.core.memory.memory_compressor import MemoryCompressor
from src.core.memory.lifecycle_manager import MemoryLifecycleManager, MemoryLayer
from src.core.monitoring.metrics import MetricsCollector
from src.core.visualization.reasoning_visualizer import (
    ReasoningVisualizer,
    VisualizationNode,
    VisualizationEdge,
)


class TestAssistantWithDistributed:
    def test_assistant_with_circuit_breaker(self):
        assistant = Assistant()
        cb = CircuitBreaker(name="test-cb", failure_threshold=3, recovery_timeout=10)

        def safe_external_call():
            return {"status": "ok"}

        assistant.register_service(
            "external_api",
            lambda: cb.execute(safe_external_call),
        )

        result = assistant.get_service("external_api")()
        assert result["status"] == "ok"

    def test_assistant_with_event_bus(self):
        assistant = Assistant()
        bus = EventBus()
        event_log = []

        def log_event(event):
            event_log.append(event)

        bus.subscribe(log_event, event_type=EventType.CUSTOM)

        def action_with_event():
            event = DomainEvent.create(
                event_type=EventType.CUSTOM,
                aggregate_id="agg-1",
                aggregate_type="assistant",
                payload={"action": "test"},
                source="assistant",
            )
            bus.publish(event)
            return "done"

        assistant.register_service("action_with_event", action_with_event)
        assistant.get_service("action_with_event")()
        assert len(event_log) == 1
        assert event_log[0].event_type == EventType.CUSTOM


class TestAssistantWithCognition:
    async def test_assistant_with_reasoning_coordinator(self):
        assistant = Assistant()
        coordinator = AdvancedReasoningCoordinator()

        async def solve(question):
            return await coordinator.solve_problem(
                question, strategy=ReasoningStrategy.TREE_OF_THOUGHT
            )

        assistant.register_service("advanced_reasoning", solve)
        service = assistant.get_service("advanced_reasoning")
        result = await service("这是一个需要多步骤思考的问题")
        assert result is not None
        assert result.strategy == "tree_of_thought"


class TestAssistantWithMemory:
    def test_assistant_with_memory_compressor(self):
        assistant = Assistant()
        compressor = MemoryCompressor()
        from datetime import datetime

        test_memories = [
            {
                "id": f"m{i}",
                "content": f"记忆内容 {i}",
                "importance": 0.5 + i * 0.05,
                "created_at": datetime.now().isoformat(),
            }
            for i in range(20)
        ]

        def compress_memories():
            return compressor.compress(
                test_memories, strategy="importance", keep_ratio=0.5
            )

        assistant.register_service("compress_memories", compress_memories)
        service = assistant.get_service("compress_memories")
        result = service()
        assert result.original_count == 20
        assert result.compressed_count <= 10

    def test_assistant_with_lifecycle_manager(self):
        assistant = Assistant()
        lifecycle_manager = MemoryLifecycleManager()

        def check_memory_lifecycle(memory, layer):
            return {
                "should_promote": lifecycle_manager.should_promote(memory, layer),
                "should_demote": lifecycle_manager.should_demote(memory, layer),
                "should_expire": lifecycle_manager.should_expire(memory, layer),
            }

        assistant.register_service("memory_lifecycle_check", check_memory_lifecycle)
        from datetime import datetime

        test_memory = {
            "id": "m1",
            "content": "测试记忆",
            "importance": 0.9,
            "access_count": 15,
            "created_at": datetime.now().isoformat(),
        }
        service = assistant.get_service("memory_lifecycle_check")
        result = service(test_memory, MemoryLayer.SHORT_TERM)
        assert result["should_promote"] is True


class TestAssistantWithMonitoring:
    def test_assistant_with_metrics(self):
        assistant = Assistant()
        metrics = MetricsCollector()

        original_process = getattr(assistant, "process", None)

        @metrics.measure_performance("assistant_process")
        def monitored_process(*args, **kwargs):
            if original_process:
                return original_process(*args, **kwargs)
            return {"status": "ok"}

        assistant.process = monitored_process
        assistant.register_service(
            "get_metrics",
            lambda: metrics.get_statistics(),
        )

        for _ in range(5):
            assistant.process("test")

        stats = assistant.get_service("get_metrics")()
        assert stats["performance"]["assistant_process"]["count"] == 5


class TestAssistantWithVisualization:
    def test_assistant_with_visualizer(self):
        assistant = Assistant()
        visualizer = ReasoningVisualizer()

        def create_simple_visualization():
            tree_data = {
                "tree_structure": {
                    "id": "root",
                    "content": "根问题",
                    "type": "root",
                    "value": 1.0,
                    "confidence": 1.0,
                    "children": [
                        {
                            "id": "a",
                            "content": "方案A",
                            "type": "thought",
                            "value": 0.8,
                            "confidence": 0.6,
                            "children": [],
                        },
                        {
                            "id": "b",
                            "content": "方案B",
                            "type": "thought",
                            "value": 0.6,
                            "confidence": 0.5,
                            "children": [],
                        },
                    ],
                }
            }
            viz_data = visualizer.visualize_tree_of_thought(tree_data)
            return visualizer.to_json(viz_data)

        assistant.register_service("create_visualization", create_simple_visualization)
        service = assistant.get_service("create_visualization")
        json_str = service()
        assert isinstance(json_str, str)
        assert "nodes" in json_str


class TestFullWorkflow:
    async def test_complex_workflow(self):
        assistant = Assistant()
        coordinator = AdvancedReasoningCoordinator()
        bus = EventBus()
        metrics = MetricsCollector()
        compressor = MemoryCompressor()

        reasoning_result = await coordinator.solve_problem(
            "测试问题", strategy=ReasoningStrategy.TREE_OF_THOUGHT
        )

        memory = {
            "id": "workflow_test",
            "content": f"推理结果: {reasoning_result.solution or ''}",
            "importance": 0.8,
            "metadata": {"source": "workflow_test"},
        }

        event = DomainEvent.create(
            event_type=EventType.CUSTOM,
            aggregate_id="workflow-1",
            aggregate_type="integration_test",
            payload={"result": "success"},
            source="integration_test",
        )
        bus.publish(event)

        metrics.increment_counter("workflow_executions")

        assert reasoning_result is not None
        assert metrics.counters["workflow_executions"] == 1


class TestHealthCheckIntegration:
    def test_system_health_check(self):
        checker = HealthChecker()

        checker.register_check(
            "memory_system",
            lambda: HealthCheck(
                name="memory_system",
                status=HealthStatus.HEALTHY,
                message="Memory system OK",
                details={"items": 1000},
            ),
        )

        checker.register_check(
            "event_bus",
            lambda: HealthCheck(
                name="event_bus",
                status=HealthStatus.HEALTHY,
                message="Event bus OK",
                details={"queue_length": 0},
            ),
        )

        results = checker.check_all()
        assert results["overall_status"] == "healthy"
        assert len(results["checks"]) == 2
        check_names = [c["name"] for c in results["checks"]]
        assert "memory_system" in check_names
        assert "event_bus" in check_names


class TestSagaWithAssistant:
    def test_saga_orchestration_workflow(self):
        assistant = Assistant()
        orchestrator = SagaOrchestrator()
        tx_id = orchestrator.create_transaction("assistant_workflow")
        step1_done = False
        step2_done = False

        def step1():
            nonlocal step1_done
            step1_done = True
            return True

        def step2():
            nonlocal step2_done
            step2_done = True
            return True

        orchestrator.add_step(tx_id, "step1", step1, None)
        orchestrator.add_step(tx_id, "step2", step2, None)
        result = orchestrator.execute(tx_id)
        assert result["success"] is True
        assert step1_done is True
        assert step2_done is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
