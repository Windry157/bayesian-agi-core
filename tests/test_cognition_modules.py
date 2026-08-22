#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试：补齐后的认知模块
覆盖 chain_of_thought, cognition_coordinator, advanced_reasoning_coordinator, multi_agent_orchestrator
"""

import pytest
import asyncio
import time
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

# 添加源码路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.core.cognition.chain_of_thought import (
    ChainOfThought, ChainResult, ReasoningStep, ChainStrategy
)
from src.core.cognition.cognition_coordinator import (
    CognitionCoordinator, DecisionMode, DecisionResult
)
from src.core.cognition.advanced_reasoning_coordinator import (
    AdvancedReasoningCoordinator, ReasoningStrategy, ReasoningResult
)
from src.core.cognition.multi_agent_orchestrator import (
    MultiAgentOrchestrator, Task, TaskStatus, LLMGeneralAgent
)


# ================================================================
# Test: ChainOfThought
# ================================================================

class TestChainOfThought:
    """测试 ChainOfThought 补齐后的功能"""

    def test_init_default(self):
        """默认初始化"""
        cot = ChainOfThought()
        assert cot.max_chain_length == 10
        assert cot.default_strategy == ChainStrategy.STANDARD
        assert cot.consistency_samples == 3
        assert cot.llm is None

    def test_init_with_config(self):
        """带配置初始化"""
        cot = ChainOfThought(config={
            "max_chain_length": 20,
            "default_strategy": "self_consistency",
            "consistency_samples": 5,
        })
        assert cot.max_chain_length == 20
        assert cot.default_strategy == ChainStrategy.SELF_CONSISTENCY
        assert cot.consistency_samples == 5

    def test_fallback_template(self):
        """无 LLM 时回退到模板推理"""
        cot = ChainOfThought()
        chain = cot.generate_chain("测试问题", {"key": "val"})
        assert len(chain) == 5
        assert chain[0]["step"] == 1
        assert chain[0]["type"] == "understanding"
        assert chain[4]["step"] == 5
        assert chain[4]["type"] == "decision"

    def test_parse_response_with_steps(self):
        """解析含步骤的 LLM 回复"""
        cot = ChainOfThought()
        text = """步骤 1：分析用户需求。
步骤 2：评估技术方案。
步骤 3：选择最优解。
结论：使用方案 A。"""
        steps, conclusion = cot._parse_response(text)
        assert len(steps) == 3
        assert steps[0].content == "分析用户需求。"
        assert steps[2].content == "选择最优解。"
        assert conclusion == "使用方案 A。"

    def test_parse_response_without_steps(self):
        """解析不含步骤的回复"""
        cot = ChainOfThought()
        steps, conclusion = cot._parse_response("直接回答：答案是42。")
        assert len(steps) == 0
        assert conclusion == "直接回答：答案是42。"

    def test_parse_response_empty(self):
        """解析空回复"""
        cot = ChainOfThought()
        steps, conclusion = cot._parse_response("")
        assert len(steps) == 0
        assert conclusion == ""

    def test_infer_confidence(self):
        """置信度推断"""
        cot = ChainOfThought()
        steps = [
            ReasoningStep(1, "步骤1", "内容1" * 10),  # > 200 chars
            ReasoningStep(2, "步骤2", "内容2"),
        ]
        # 两步 + 内容长
        conf = cot._infer_confidence(steps, "结论")
        assert 0.6 <= conf <= 0.99

    def test_infer_confidence_low(self):
        """低置信度场景"""
        cot = ChainOfThought()
        conf = cot._infer_confidence([], "")
        assert conf == 0.3

    def test_majority_vote(self):
        """多数投票"""
        cot = ChainOfThought()
        candidates = ["A", "A", "B", "A", "C"]
        assert cot._majority_vote(candidates) == "A"

    def test_majority_vote_empty(self):
        """空投票"""
        cot = ChainOfThought()
        assert cot._majority_vote([]) == ""

    def test_parse_sub_questions(self):
        """解析子问题"""
        cot = ChainOfThought()
        text = "- 分析市场需求\n- 评估竞品\n1. 确定目标用户"
        questions = cot._parse_sub_questions(text)
        assert len(questions) == 3

    def test_old_chain_format_compatibility(self):
        """旧版链格式兼容"""
        cot = ChainOfThought()
        chain = cot._make_old_chain("旧问题")
        assert len(chain) == 5
        for step in chain:
            assert "step" in step
            assert "type" in step
            assert "content" in step

    @pytest.mark.asyncio
    async def test_reason_with_mock_llm(self):
        """使用模拟 LLM 进行推理"""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "步骤 1：分析。\n结论：完成。"
        mock_llm.generate = MagicMock(return_value=mock_response)

        cot = ChainOfThought(llm=mock_llm)
        cot._call_llm = AsyncMock(return_value="步骤 1：分析。\n结论：完成。")

        result = await cot.reason("测试问题")
        assert isinstance(result, ChainResult)
        assert result.problem == "测试问题"
        assert result.strategy == "standard"
        assert len(result.steps) > 0
        assert result.conclusion

    @pytest.mark.asyncio
    async def test_reason_fallback_on_llm_error(self):
        """LLM 失败时回退"""
        mock_llm = MagicMock()
        mock_llm.generate.side_effect = Exception("LLM failure")

        cot = ChainOfThought(llm=mock_llm)
        result = await cot.reason("问题")
        # 应返回降级结果，不抛异常
        assert isinstance(result, ChainResult)


# ================================================================
# Test: CognitionCoordinator
# ================================================================

class TestCognitionCoordinator:
    """测试 CognitionCoordinator 补齐后的功能"""

    def test_auto_initialize_subsystems(self):
        """自动初始化 System1 + System2 + BayesianBrain"""
        coord = CognitionCoordinator()
        assert coord.system1 is not None
        assert coord.system2 is not None
        assert coord.bayesian_brain is not None
        assert coord.confidence_threshold == 0.7
        assert coord.mode == DecisionMode.SYSTEM1_FAST

    def test_custom_parameters(self):
        """自定义参数初始化"""
        coord = CognitionCoordinator(
            confidence_threshold=0.8,
            mode=DecisionMode.SYSTEM2_DEEP,
        )
        assert coord.confidence_threshold == 0.8
        assert coord.mode == DecisionMode.SYSTEM2_DEEP

    def test_system1_only_mode(self):
        """仅 System1 模式"""
        coord = CognitionCoordinator()
        result = coord.make_decision({"routine": True}, mode=DecisionMode.SYSTEM1_ONLY)
        assert isinstance(result, DecisionResult)
        assert result.mode == DecisionMode.SYSTEM1_ONLY
        assert result.system1_result is not None
        assert result.decision is not None

    def test_system1_fast_mode_high_confidence(self):
        """System1 快速模式 - 高置信度直接输出"""
        coord = CognitionCoordinator(confidence_threshold=0.5)
        result = coord.make_decision({"routine": True}, mode=DecisionMode.SYSTEM1_FAST)
        assert result.mode == DecisionMode.SYSTEM1_FAST
        # routine 场景 System1 通常置信度高

    def test_system2_deep_mode(self):
        """深度分析模式"""
        coord = CognitionCoordinator()
        result = coord.make_decision({"novel": True}, mode=DecisionMode.SYSTEM2_DEEP)
        assert result.mode == DecisionMode.SYSTEM2_DEEP
        assert result.system2_result is not None

    def test_hybrid_fuse_mode(self):
        """融合模式"""
        coord = CognitionCoordinator()
        result = coord.make_decision({"routine": True}, mode=DecisionMode.HYBRID_FUSE)
        assert result.mode == DecisionMode.HYBRID_FUSE
        if result.fusion_details:
            assert "method" in result.fusion_details

    def test_parallel_mode(self):
        """并行投票模式"""
        coord = CognitionCoordinator()
        result = coord.make_decision({"routine": True}, mode=DecisionMode.PARALLEL)
        assert result.mode == DecisionMode.PARALLEL
        assert result.system1_result is not None
        assert result.system2_result is not None

    def test_set_confidence_threshold(self):
        """设置置信度阈值"""
        coord = CognitionCoordinator()
        coord.set_confidence_threshold(0.9)
        assert coord.confidence_threshold == 0.9

    def test_set_mode(self):
        """设置模式"""
        coord = CognitionCoordinator()
        coord.set_mode(DecisionMode.SYSTEM2_DEEP)
        assert coord.mode == DecisionMode.SYSTEM2_DEEP

    def test_statistics(self):
        """统计信息"""
        coord = CognitionCoordinator()
        coord.make_decision({})
        stats = coord.get_statistics()
        assert stats["total_decisions"] >= 1
        assert "mode" in stats
        assert "decisions_by_mode" in stats

    def test_history(self):
        """决策历史"""
        coord = CognitionCoordinator()
        for i in range(5):
            coord.make_decision({"test": i})
        history = coord.get_history(limit=3)
        assert len(history) == 3

    def test_clear_history(self):
        """清空历史"""
        coord = CognitionCoordinator()
        coord.make_decision({})
        coord.clear_history()
        assert len(coord.decision_history) == 0


# ================================================================
# Test: AdvancedReasoningCoordinator
# ================================================================

class TestAdvancedReasoningCoordinator:
    """测试 AdvancedReasoningCoordinator 补齐后的功能"""

    def test_init(self):
        """初始化"""
        arc = AdvancedReasoningCoordinator()
        assert arc.tot_reasoner is not None
        assert arc.graph_engine is not None
        assert arc.causal_engine is not None

    @pytest.mark.asyncio
    async def test_solve_with_graph(self):
        """图推理"""
        arc = AdvancedReasoningCoordinator()
        result = await arc.solve_problem(
            "测试图推理",
            strategy=ReasoningStrategy.GRAPH_REASONING,
            entities=["实体A", "实体B", "实体C"],
            source="实体A",
            target="实体C",
        )
        assert isinstance(result, ReasoningResult)
        assert result.strategy == "graph_reasoning"

    @pytest.mark.asyncio
    async def test_solve_with_causal(self):
        """因果推理"""
        arc = AdvancedReasoningCoordinator()
        result = await arc.solve_problem(
            "测试因果推理",
            strategy=ReasoningStrategy.CAUSAL_REASONING,
            variables=[
                {"id": "x", "name": "原因"},
                {"id": "y", "name": "结果"},
            ],
            relations=[
                {"cause": "x", "effect": "y", "strength": 0.8},
            ],
            cause="x",
            effect="y",
        )
        assert isinstance(result, ReasoningResult)
        assert result.strategy == "causal_reasoning"
        assert result.details.get("causal_effect") is not None

    @pytest.mark.asyncio
    async def test_solve_with_tot_fallback(self):
        """ToT 推理（无 LLM 回退）"""
        arc = AdvancedReasoningCoordinator()
        result = await arc.solve_problem(
            "测试树状思维",
            strategy=ReasoningStrategy.TREE_OF_THOUGHT,
        )
        assert isinstance(result, ReasoningResult)
        assert result.strategy == "tree_of_thought"

    @pytest.mark.asyncio
    async def test_solve_hybrid(self):
        """混合策略"""
        arc = AdvancedReasoningCoordinator()
        result = await arc.solve_problem(
            "测试混合策略",
            strategy=ReasoningStrategy.HYBRID,
            entities=["实体A"],
            variables=[{"id": "x", "name": "变量"}],
        )
        assert isinstance(result, ReasoningResult)
        assert result.strategy == "hybrid"

    def test_get_statistics(self):
        """统计信息"""
        arc = AdvancedReasoningCoordinator()
        stats = arc.get_statistics()
        assert "strategy_usage" in stats

    def test_reset(self):
        """重置"""
        arc = AdvancedReasoningCoordinator()
        arc._solve_with_graph("测试", entities=["E1"])
        assert len(arc.graph_engine.entities) > 0
        arc.reset()
        assert len(arc.graph_engine.entities) == 0
        assert len(arc.causal_engine.graph.variables) == 0


# ================================================================
# Test: MultiAgentOrchestrator
# ================================================================

class TestMultiAgentOrchestrator:
    """测试 MultiAgentOrchestrator 补齐后的功能"""

    @pytest.mark.asyncio
    async def test_basic_workflow(self):
        """基础工作流"""
        orchestrator = MultiAgentOrchestrator()

        # 注册通用 LLM Agent（无 LLM 回退）
        orchestrator.register_agent(LLMGeneralAgent())

        tasks = [
            Task(id="t1", name="任务1", description="测试任务1",
                 agent_type="LLMGeneralAgent"),
            Task(id="t2", name="任务2", description="测试任务2",
                 agent_type="LLMGeneralAgent", dependencies=["t1"]),
        ]
        orchestrator.add_tasks(tasks)
        results = await orchestrator.run_workflow()

        assert results["t1"].status == TaskStatus.COMPLETED
        assert results["t2"].status == TaskStatus.COMPLETED
        assert results["t2"].input_data.get("任务1_data") is not None

    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """并行执行"""
        orchestrator = MultiAgentOrchestrator()
        orchestrator.register_agent(LLMGeneralAgent())

        tasks = [
            Task(id="p1", name="并行1", description="并行任务1",
                 agent_type="LLMGeneralAgent"),
            Task(id="p2", name="并行2", description="并行任务2",
                 agent_type="LLMGeneralAgent"),
            Task(id="p3", name="并行3", description="并行任务3",
                 agent_type="LLMGeneralAgent"),
        ]
        orchestrator.add_tasks(tasks)
        results = await orchestrator.run_workflow()

        for tid in ["p1", "p2", "p3"]:
            assert results[tid].status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_dependency_ordering(self):
        """依赖顺序"""
        orchestrator = MultiAgentOrchestrator()
        orchestrator.register_agent(LLMGeneralAgent())

        tasks = [
            Task(id="a", name="A", description="任务A", agent_type="LLMGeneralAgent"),
            Task(id="b", name="B", description="任务B", agent_type="LLMGeneralAgent",
                 dependencies=["a"]),
            Task(id="c", name="C", description="任务C", agent_type="LLMGeneralAgent",
                 dependencies=["b"]),
        ]
        orchestrator.add_tasks(tasks)

        # 检查就绪状态
        ready = orchestrator.get_ready_tasks()
        assert "a" in ready
        assert "b" not in ready
        assert "c" not in ready

    @pytest.mark.asyncio
    async def test_llm_agent_no_llm(self):
        """通用 LLM Agent 无 LLM 时正常工作"""
        agent = LLMGeneralAgent()
        task = Task(id="t", name="测试", description="无LLM测试",
                    agent_type="LLMGeneralAgent")
        result = await agent.execute(task)
        assert result.status == TaskStatus.COMPLETED
        assert result.output_data is not None
        assert "result" in result.output_data

    @pytest.mark.asyncio
    async def test_demo_agents_backward_compat(self):
        """示例 Agent 保持向后兼容"""
        orchestrator = MultiAgentOrchestrator()
        orchestrator.register_agent_by_type("MarketResearchAgent")
        orchestrator.register_agent_by_type("FinancialForecastAgent")

        task = Task(id="d1", name="市场调研", description="测试",
                    agent_type="MarketResearchAgent")
        orchestrator.add_task(task)
        results = await orchestrator.run_workflow()
        assert results["d1"].status == TaskStatus.COMPLETED

    def test_efficiency_metrics(self):
        """效率指标"""
        orchestrator = MultiAgentOrchestrator()
        metrics = orchestrator.calculate_efficiency_metrics()
        assert "total_tasks" in metrics
        assert "completed_tasks" in metrics
        assert metrics["total_tasks"] == 0  # 无任务

    def test_workflow_graph(self):
        """工作流 DAG 图"""
        orchestrator = MultiAgentOrchestrator()
        orchestrator.add_task(Task(id="n1", name="节点1", description="",
                                    agent_type="LLMGeneralAgent",
                                    dependencies=["n2"]))
        orchestrator.add_task(Task(id="n2", name="节点2", description="",
                                    agent_type="LLMGeneralAgent"))
        graph = orchestrator.get_workflow_graph()
        assert len(graph["nodes"]) == 2
        assert len(graph["edges"]) == 1


# ================================================================
# Test: Integration
# ================================================================

class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_cot_inside_cognition_coordinator(self):
        """ChainOfThought 与 CognitionCoordinator 协同"""
        cot = ChainOfThought()
        coord = CognitionCoordinator()

        # CoT 作为 System2 的辅助推理模块
        chain_result = await cot.reason("集成测试问题")
        assert isinstance(chain_result, ChainResult)

        # Coordinator 正常决策
        decision = coord.make_decision({"test": "integration"})
        assert decision.decision is not None

    def test_multi_strategy_coordinator_init(self):
        """多推理策略协调器初始化"""
        arc = AdvancedReasoningCoordinator()
        assert arc.tot_reasoner is not None
        assert arc.graph_engine is not None
        assert arc.causal_engine is not None
        # 确保互不干扰
        assert len(arc.graph_engine.entities) == 0
        assert len(arc.causal_engine.graph.variables) == 0
