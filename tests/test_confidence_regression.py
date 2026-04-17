#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
置信度评分回归测试集
包含黄金数据集和边界情况测试，确保置信度评分系统的稳定性
"""

import pytest
import asyncio
from typing import Dict, List, Any
from datetime import datetime


class TestConfidenceScorer:
    """置信度评分器测试类"""

    @pytest.fixture
    def scorer(self):
        """创建置信度评分器实例"""
        from src.core.uncertainty.confidence_scorer import ConfidenceScorer
        return ConfidenceScorer()

    @pytest.mark.asyncio
    async def test_decision_confidence_basic(self, scorer):
        """测试决策置信度基本功能"""
        decision_context = {
            "input": "什么是人工智能？",
            "thought_chain": [
                {"type": "understanding", "content": "理解输入"}
            ],
            "context": {"relevant_history": ["AI相关"]}
        }

        result = await scorer.score_decision_confidence(
            decision_context=decision_context,
            relevant_memories=[{"similarity": 0.8}, {"similarity": 0.6}],
            knowledge_coverage=0.7
        )

        assert "confidence_score" in result
        assert 0 <= result["confidence_score"] <= 1
        assert "confidence_level" in result
        assert result["confidence_level"] in ["high", "medium", "low", "very_low", "unknown"]
        assert "factor_scores" in result

    @pytest.mark.asyncio
    async def test_decision_confidence_with_no_memories(self, scorer):
        """测试无记忆情况的决策置信度"""
        decision_context = {
            "input": "随机问题12345",
            "thought_chain": [],
            "context": {}
        }

        result = await scorer.score_decision_confidence(
            decision_context=decision_context,
            relevant_memories=[],
            knowledge_coverage=0.2
        )

        assert 0 <= result["confidence_score"] <= 1
        assert result["confidence_level"] in ["high", "medium", "low", "very_low", "unknown"]

    @pytest.mark.asyncio
    async def test_text_generation_confidence_basic(self, scorer):
        """测试文本生成置信度基本功能"""
        result = await scorer.score_text_generation_confidence(
            prompt="什么是人工智能？",
            generated_text="人工智能是机器模拟人类智能的技术。",
            model_output={"confidence": 0.85}
        )

        assert "confidence_score" in result
        assert 0 <= result["confidence_score"] <= 1
        assert "confidence_level" in result
        assert "factor_scores" in result

    @pytest.mark.asyncio
    async def test_text_generation_confidence_empty_text(self, scorer):
        """测试空文本的置信度处理"""
        result = await scorer.score_text_generation_confidence(
            prompt="问题",
            generated_text="",
            model_output=None
        )

        assert "confidence_score" in result
        assert result["confidence_score"] >= 0

    @pytest.mark.asyncio
    async def test_confidence_thresholds(self, scorer):
        """测试置信度阈值设置和获取"""
        original_thresholds = scorer.get_confidence_thresholds()

        assert "high" in original_thresholds
        assert "medium" in original_thresholds
        assert "low" in original_thresholds
        assert "very_low" in original_thresholds

        scorer.set_confidence_threshold("high", 0.85)
        new_thresholds = scorer.get_confidence_thresholds()
        assert new_thresholds["high"] == 0.85

        scorer.set_confidence_threshold("high", original_thresholds["high"])

    def test_confidence_classification(self, scorer):
        """测试置信度分类逻辑"""
        assert scorer._classify_confidence(0.9) == "high"
        assert scorer._classify_confidence(0.7) == "medium"
        assert scorer._classify_confidence(0.5) == "low"
        assert scorer._classify_confidence(0.1) == "very_low"

    def test_memory_match_score_calculation(self, scorer):
        """测试记忆匹配度计算"""
        empty_memories = []
        assert scorer._calculate_memory_match_score(empty_memories) < 0.3

        low_similarity_memories = [{"similarity": 0.2}, {"similarity": 0.3}]
        score = scorer._calculate_memory_match_score(low_similarity_memories)
        assert 0.1 <= score <= 0.5

        high_similarity_memories = [{"similarity": 0.9}, {"similarity": 0.85}, {"similarity": 0.88}]
        score = scorer._calculate_memory_match_score(high_similarity_memories)
        assert 0.7 <= score <= 0.95

    def test_context_consistency_calculation(self, scorer):
        """测试上下文一致性计算"""
        complete_context = {
            "input": "测试输入",
            "thought_chain": [1, 2, 3],
            "context": {"relevant_history": [1, 2]}
        }
        score = scorer._calculate_context_consistency(complete_context)
        assert score >= 0.7

        incomplete_context = {
            "input": "测试输入"
        }
        score = scorer._calculate_context_consistency(incomplete_context)
        assert score < 0.5

    def test_text_consistency_calculation(self, scorer):
        """测试文本一致性计算"""
        consistent_text = "人工智能是机器模拟人类智能的技术。它涉及机器学习和深度学习。"
        score = scorer._calculate_text_consistency(consistent_text)
        assert 0.3 <= score <= 0.9

        repetitive_text = "testing analysis testing analysis testing"
        score = scorer._calculate_text_consistency(repetitive_text)
        assert score < 0.5

    def test_prompt_relevance_calculation(self, scorer):
        """测试提示相关性计算"""
        relevant_text = "artificial intelligence machine learning"
        score = scorer._calculate_prompt_relevance("artificial intelligence", relevant_text)
        assert score > 0.3

        irrelevant_text = "today weather is good"
        score = scorer._calculate_prompt_relevance("artificial intelligence", irrelevant_text)
        assert score < 0.3


class TestResponseWrapper:
    """响应包装器测试类"""

    @pytest.fixture
    def wrapper(self):
        """创建响应包装器实例"""
        from src.core.uncertainty.response_wrapper import ResponseWrapper
        return ResponseWrapper()

    @pytest.mark.asyncio
    async def test_wrap_consciousness_response(self, wrapper):
        """测试意识系统响应包装"""
        consciousness_result = {
            "thought_chain": [
                {"type": "understanding", "content": "理解输入"},
                {"type": "conclusion", "content": "人工智能是机器模拟人类智能"}
            ],
            "decision": {
                "type": "information",
                "content": "人工智能是机器模拟人类智能的技术。",
                "confidence": 0.75
            },
            "context_used": {"relevant_history_count": 2},
            "memories_used": 3
        }

        wrapped = await wrapper.wrap_consciousness_response(
            consciousness_result=consciousness_result,
            input_text="什么是人工智能？",
            session_id="test_session"
        )

        assert "answer" in wrapped
        assert "confidence" in wrapped
        assert isinstance(wrapped["confidence"], (int, float))
        assert 0 <= wrapped["confidence"] <= 1
        assert "confidence_details" in wrapped
        assert "timestamp" in wrapped

    @pytest.mark.asyncio
    async def test_wrap_text_generation_response(self, wrapper):
        """测试文本生成响应包装"""
        generation_result = {
            "text": "人工智能是机器模拟人类智能的技术。",
            "model": "deepseek-r1:7b",
            "generation_time": 1.5,
            "confidence": {
                "confidence_score": 0.8,
                "confidence_level": "high"
            }
        }

        wrapped = await wrapper.wrap_text_generation_response(
            generation_result=generation_result,
            input_text="什么是人工智能？",
            session_id="test_session"
        )

        assert "answer" in wrapped
        assert "confidence" in wrapped
        assert wrapped["model"] == "deepseek-r1:7b"

    @pytest.mark.asyncio
    async def test_wrap_decision_response(self, wrapper):
        """测试决策响应包装"""
        decision_result = {
            "type": "action",
            "content": "执行搜索操作",
            "confidence": 0.7
        }

        wrapped = await wrapper.wrap_decision_response(
            decision_result=decision_result,
            input_text="搜索相关信息",
            session_id="test_session"
        )

        assert "answer" in wrapped
        assert "confidence" in wrapped
        assert wrapped["decision_type"] == "action"

    @pytest.mark.asyncio
    async def test_error_response_creation(self, wrapper):
        """测试错误响应创建"""
        error_response = wrapper._create_error_response(
            input_text="测试输入",
            error="测试错误",
            session_id="test_session"
        )

        assert "answer" in error_response
        assert error_response["confidence"] == 0.0
        assert error_response["error"] is True
        assert "error_message" in error_response

    @pytest.mark.asyncio
    async def test_wrap_any_response_auto_detection(self, wrapper):
        """测试自动检测响应类型"""
        consciousness_response = {
            "thought_chain": [],
            "decision": {}
        }

        wrapped = await wrapper.wrap_any_response(
            raw_response=consciousness_response,
            input_text="测试",
            response_type="auto"
        )

        assert "answer" in wrapped
        assert "confidence" in wrapped


class TestFeedbackCollector:
    """反馈收集器测试类"""

    @pytest.fixture
    def collector(self, tmp_path):
        """创建反馈收集器实例"""
        from src.core.uncertainty.feedback_collector import FeedbackCollector
        storage_dir = str(tmp_path / "feedback_test")
        return FeedbackCollector(storage_dir=storage_dir)

    @pytest.mark.asyncio
    async def test_submit_correct_feedback(self, collector):
        """测试提交正确反馈"""
        system_response = {
            "answer": "人工智能是机器模拟人类智能",
            "confidence": 0.85
        }

        result = await collector.submit_feedback(
            session_id="test_session",
            input_text="什么是人工智能？",
            system_response=system_response,
            feedback_type="correct",
            confidence_score=0.85
        )

        assert result["success"] is True
        assert "feedback_id" in result

    @pytest.mark.asyncio
    async def test_submit_incorrect_feedback_with_correction(self, collector):
        """测试提交错误反馈并提供修正"""
        system_response = {
            "answer": "人工智能是机器模拟人类智能",
            "confidence": 0.85
        }

        result = await collector.submit_feedback(
            session_id="test_session",
            input_text="什么是人工智能？",
            system_response=system_response,
            feedback_type="incorrect",
            user_correction="人工智能是计算机科学的一个分支"
        )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_submit_invalid_feedback_type(self, collector):
        """测试提交无效反馈类型"""
        system_response = {"answer": "测试回答"}

        result = await collector.submit_feedback(
            session_id="test_session",
            input_text="测试输入",
            system_response=system_response,
            feedback_type="invalid_type"
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_feedback_stats(self, collector):
        """测试获取反馈统计"""
        system_response = {"answer": "测试回答", "confidence": 0.5}

        await collector.submit_feedback(
            session_id="session1",
            input_text="输入1",
            system_response=system_response,
            feedback_type="correct"
        )

        await collector.submit_feedback(
            session_id="session2",
            input_text="输入2",
            system_response=system_response,
            feedback_type="incorrect"
        )

        stats = await collector.get_feedback_stats()

        assert stats["total"] == 2
        assert stats["by_type"]["correct"] == 1
        assert stats["by_type"]["incorrect"] == 1

    @pytest.mark.asyncio
    async def test_get_calibration_data(self, collector):
        """测试获取校准数据"""
        system_response = {"answer": "测试回答", "confidence": 0.7}

        await collector.submit_feedback(
            session_id="session1",
            input_text="输入1",
            system_response=system_response,
            feedback_type="correct"
        )

        await collector.submit_feedback(
            session_id="session2",
            input_text="输入2",
            system_response=system_response,
            feedback_type="uncertain"
        )

        calibration_data = await collector.get_feedback_for_confidence_calibration()

        assert len(calibration_data) == 1
        assert calibration_data[0]["was_correct"] is True


class TestConfidenceIntegration:
    """置信度评分集成测试"""

    @pytest.mark.asyncio
    async def test_full_confidence_workflow(self):
        """测试完整置信度工作流"""
        from src.core.uncertainty.confidence_scorer import confidence_scorer
        from src.core.uncertainty.response_wrapper import response_wrapper

        decision_context = {
            "input": "人工智能的定义是什么？",
            "thought_chain": [
                {"type": "understanding", "content": "理解输入"},
                {"type": "analysis", "content": "分析问题"},
                {"type": "conclusion", "content": "生成答案"}
            ],
            "context": {"relevant_history": ["AI相关历史"]}
        }

        decision_result = await confidence_scorer.score_decision_confidence(
            decision_context=decision_context,
            relevant_memories=[
                {"similarity": 0.8, "content": "人工智能相关"},
                {"similarity": 0.7, "content": "机器学习相关"}
            ],
            knowledge_coverage=0.75
        )

        consciousness_response = {
            "thought_chain": decision_context["thought_chain"],
            "decision": {
                "type": "information",
                "content": "人工智能是机器模拟人类智能的技术。",
                "confidence": decision_result["confidence_score"]
            },
            "context_used": {"relevant_history_count": 1},
            "memories_used": 2
        }

        wrapped = await response_wrapper.wrap_consciousness_response(
            consciousness_result=consciousness_response,
            input_text=decision_context["input"],
            session_id="integration_test"
        )

        assert "answer" in wrapped
        assert "confidence" in wrapped
        assert 0 <= wrapped["confidence"] <= 1

    @pytest.mark.asyncio
    async def test_confidence_with_edge_cases(self):
        """测试边界情况处理"""
        from src.core.uncertainty.confidence_scorer import confidence_scorer

        edge_cases = [
            {
                "name": "极短输入",
                "input": "AI",
                "expected_confidence_range": (0.1, 0.9)
            },
            {
                "name": "极长输入",
                "input": "AI " * 100,
                "expected_confidence_range": (0.1, 0.9)
            },
            {
                "name": "特殊字符",
                "input": "!@#$%^&*()",
                "expected_confidence_range": (0.0, 0.5)
            },
            {
                "name": "纯数字",
                "input": "12345",
                "expected_confidence_range": (0.0, 0.7)
            }
        ]

        for case in edge_cases:
            result = await confidence_scorer.score_decision_confidence(
                decision_context={
                    "input": case["input"],
                    "thought_chain": [],
                    "context": {}
                },
                relevant_memories=[],
                knowledge_coverage=0.5
            )

            min_exp, max_exp = case["expected_confidence_range"]
            assert min_exp <= result["confidence_score"] <= max_exp, \
                f"Case '{case['name']}' failed: {result['confidence_score']} not in range"


class TestConfidenceThresholds:
    """置信度阈值策略测试"""

    def test_threshold_boundary_high_confidence(self):
        """测试高置信度边界"""
        from src.core.uncertainty.confidence_scorer import ConfidenceScorer
        scorer = ConfidenceScorer()

        assert scorer._classify_confidence(0.8) == "high"
        assert scorer._classify_confidence(0.85) == "high"
        assert scorer._classify_confidence(0.79) == "medium"

    def test_threshold_boundary_medium_confidence(self):
        """测试中等置信度边界"""
        from src.core.uncertainty.confidence_scorer import ConfidenceScorer
        scorer = ConfidenceScorer()

        assert scorer._classify_confidence(0.6) == "medium"
        assert scorer._classify_confidence(0.65) == "medium"
        assert scorer._classify_confidence(0.59) == "low"

    def test_threshold_boundary_low_confidence(self):
        """测试低置信度边界"""
        from src.core.uncertainty.confidence_scorer import ConfidenceScorer
        scorer = ConfidenceScorer()

        assert scorer._classify_confidence(0.4) == "low"
        assert scorer._classify_confidence(0.45) == "low"
        assert scorer._classify_confidence(0.39) == "very_low"

    def test_threshold_boundary_very_low_confidence(self):
        """测试极低置信度边界"""
        from src.core.uncertainty.confidence_scorer import ConfidenceScorer
        scorer = ConfidenceScorer()

        assert scorer._classify_confidence(0.2) == "very_low"
        assert scorer._classify_confidence(0.0) == "very_low"


class TestUncertaintyAnalysis:
    """不确定性分析测试"""

    @pytest.mark.asyncio
    async def test_uncertainty_source_detection(self):
        """测试不确定性来源检测"""
        from src.core.uncertainty.confidence_scorer import confidence_scorer

        result = await confidence_scorer.score_decision_confidence(
            decision_context={"input": "测试", "thought_chain": [], "context": {}},
            relevant_memories=[],
            knowledge_coverage=0.1
        )

        assert "uncertainty_analysis" in result
        uncertainty = result["uncertainty_analysis"]

        assert "overall_uncertainty" in uncertainty
        assert "uncertainty_sources" in uncertainty
        assert uncertainty["overall_uncertainty"] > 0.5

    @pytest.mark.asyncio
    async def test_multiple_uncertainty_sources(self):
        """测试多个不确定性来源"""
        from src.core.uncertainty.confidence_scorer import confidence_scorer

        result = await confidence_scorer.score_decision_confidence(
            decision_context={"input": "", "thought_chain": [], "context": {}},
            relevant_memories=[],
            knowledge_coverage=0.1
        )

        uncertainty = result["uncertainty_analysis"]
        sources = uncertainty.get("uncertainty_sources", [])

        assert len(sources) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])