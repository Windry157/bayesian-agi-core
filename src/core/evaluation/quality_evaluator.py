#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回答质量评估器 - 综合评估回答的各个方面
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import httpx
import json
from .faithfulness_evaluator import FaithfulnessEvaluator, FaithfulnessScore
from .relevance_evaluator import RelevanceEvaluator, RelevanceScore


@dataclass
class QualityScore:
    """综合质量评分"""
    overall_score: float
    faithfulness: FaithfulnessScore
    relevance: RelevanceScore
    clarity_score: float
    completeness_score: float
    coherence_score: float
    explanation: str
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class QualityEvaluator:
    """综合质量评估器"""

    def __init__(self, ollama_url: str = "http://192.168.3.105:11434"):
        self.ollama_url = ollama_url
        self.faithfulness_evaluator = FaithfulnessEvaluator(ollama_url)
        self.relevance_evaluator = RelevanceEvaluator(ollama_url)

    async def evaluate(
        self,
        question: str,
        context: str,
        answer: str,
        retrieved_chunks: List[str] = None
    ) -> QualityScore:
        """
        综合评估回答质量

        Args:
            question: 用户问题
            context: 提供的上下文
            answer: 生成的回答
            retrieved_chunks: 检索到的文档片段

        Returns:
            QualityScore: 综合评分结果
        """
        # 评估忠实度
        faithfulness = await self.faithfulness_evaluator.evaluate(
            question, context, answer
        )

        # 评估相关性
        if retrieved_chunks:
            relevance = await self.relevance_evaluator.evaluate_combined(
                question, retrieved_chunks, answer
            )
        else:
            relevance = await self.relevance_evaluator.evaluate_answer(
                question, answer
            )

        # 评估清晰度
        clarity_score = self._evaluate_clarity(answer)

        # 评估完整性
        completeness_score = self._evaluate_completeness(question, answer)

        # 评估连贯性
        coherence_score = self._evaluate_coherence(answer)

        # 计算综合得分
        overall_score = (
            faithfulness.overall_score * 0.35 +
            relevance.overall_relevance_score * 0.30 +
            clarity_score * 0.15 +
            completeness_score * 0.10 +
            coherence_score * 0.10
        )

        # 生成总结和建议
        strengths = self._extract_strengths(
            faithfulness, relevance, clarity_score, completeness_score, coherence_score
        )
        weaknesses = self._extract_weaknesses(
            faithfulness, relevance, clarity_score, completeness_score, coherence_score
        )
        suggestions = self._generate_suggestions(strengths, weaknesses)

        explanation = self._generate_explanation(
            overall_score, strengths, weaknesses
        )

        return QualityScore(
            overall_score=overall_score,
            faithfulness=faithfulness,
            relevance=relevance,
            clarity_score=clarity_score,
            completeness_score=completeness_score,
            coherence_score=coherence_score,
            explanation=explanation,
            strengths=strengths,
            weaknesses=weaknesses,
            suggestions=suggestions
        )

    def _evaluate_clarity(self, answer: str) -> float:
        """评估清晰度"""
        if not answer:
            return 0.0

        # 检查句子长度
        sentences = re.split(r'[。！？.!?]', answer)
        avg_sentence_length = sum(len(s) for s in sentences) / max(1, len(sentences))

        # 检查段落结构
        paragraphs = [p for p in answer.split('\n') if p.strip()]

        # 检查标点符号
        punctuation_score = self._check_punctuation(answer)

        # 综合评分
        length_score = 1.0 if 10 < avg_sentence_length < 50 else 0.7
        paragraph_score = 1.0 if len(paragraphs) > 1 else 0.8

        return (length_score + paragraph_score + punctuation_score) / 3

    def _check_punctuation(self, text: str) -> float:
        """检查标点符号使用"""
        if not text:
            return 0.0

        # 简单检查：是否有基本标点
        has_end_punctuation = any(p in text for p in '。！？.!?')
        has_commas = any(p in text for p in '，,')

        return (1.0 if has_end_punctuation else 0.5) * 0.7 + (1.0 if has_commas else 0.5) * 0.3

    def _evaluate_completeness(self, question: str, answer: str) -> float:
        """评估完整性"""
        if not question or not answer:
            return 0.0

        # 提取问题关键词
        question_keywords = self._extract_keywords(question.lower())
        answer_words = self._extract_keywords(answer.lower())

        # 检查关键词覆盖
        covered_count = sum(1 for kw in question_keywords if kw in answer_words)
        coverage_score = covered_count / max(1, len(question_keywords))

        # 检查回答长度
        length_score = min(1.0, len(answer) / 150)

        return coverage_score * 0.6 + length_score * 0.4

    def _evaluate_coherence(self, answer: str) -> float:
        """评估连贯性"""
        if not answer:
            return 0.0

        # 检查连接词
        connectors = ['首先', '其次', '最后', '因此', '所以', '但是', '然而', '而且', '此外', '另外']
        has_connectors = any(c in answer for c in connectors)

        # 检查段落过渡
        paragraphs = [p for p in answer.split('\n') if p.strip()]
        has_paragraphs = len(paragraphs) > 1

        # 检查句子数量
        sentences = [s for s in re.split(r'[。！？.!?]', answer) if s.strip()]
        has_multiple_sentences = len(sentences) > 1

        return (
            (1.0 if has_connectors else 0.5) * 0.4 +
            (1.0 if has_paragraphs else 0.7) * 0.3 +
            (1.0 if has_multiple_sentences else 0.6) * 0.3
        )

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        words = re.findall(r'\b[\w\u4e00-\u9fa5]+\b', text)
        keywords = [word for word in words if len(word) > 1]
        return keywords[:20]

    def _extract_strengths(
        self,
        faithfulness: FaithfulnessScore,
        relevance: RelevanceScore,
        clarity: float,
        completeness: float,
        coherence: float
    ) -> List[str]:
        """提取优点"""
        strengths = []

        if faithfulness.overall_score >= 0.8:
            strengths.append("回答忠实于上下文，没有幻觉")

        if relevance.overall_relevance_score >= 0.8:
            strengths.append("回答与问题高度相关")

        if clarity >= 0.8:
            strengths.append("回答清晰易懂")

        if completeness >= 0.8:
            strengths.append("回答内容完整")

        if coherence >= 0.8:
            strengths.append("回答逻辑连贯")

        return strengths

    def _extract_weaknesses(
        self,
        faithfulness: FaithfulnessScore,
        relevance: RelevanceScore,
        clarity: float,
        completeness: float,
        coherence: float
    ) -> List[str]:
        """提取缺点"""
        weaknesses = []

        if faithfulness.overall_score < 0.5:
            weaknesses.append("回答可能包含未验证的信息")

        if relevance.overall_relevance_score < 0.5:
            weaknesses.append("回答与问题相关性较低")

        if clarity < 0.5:
            weaknesses.append("回答表达不够清晰")

        if completeness < 0.5:
            weaknesses.append("回答内容不够完整")

        if coherence < 0.5:
            weaknesses.append("回答逻辑连贯性不足")

        return weaknesses

    def _generate_suggestions(self, strengths: List[str], weaknesses: List[str]) -> List[str]:
        """生成改进建议"""
        suggestions = []

        if "回答可能包含未验证的信息" in weaknesses:
            suggestions.append("建议增强检索精度，确保回答基于可靠来源")

        if "回答与问题相关性较低" in weaknesses:
            suggestions.append("建议优化检索策略，提高相关文档的召回率")

        if "回答表达不够清晰" in weaknesses:
            suggestions.append("建议优化回答的结构和表达，使用更清晰的段落和标点")

        if "回答内容不够完整" in weaknesses:
            suggestions.append("建议检索更多相关文档，补充完整回答")

        if "回答逻辑连贯性不足" in weaknesses:
            suggestions.append("建议在回答中使用过渡词，增强逻辑连贯性")

        return suggestions

    def _generate_explanation(self, score: float, strengths: List[str], weaknesses: List[str]) -> str:
        """生成总体解释"""
        if score >= 0.8:
            return "回答质量优秀，完全满足需求。"
        elif score >= 0.6:
            return "回答质量良好，但有少量改进空间。"
        elif score >= 0.4:
            return "回答质量一般，需要多方面改进。"
        else:
            return "回答质量较差，需要全面优化。"

    async def evaluate_with_llm(
        self,
        question: str,
        context: str,
        answer: str,
        retrieved_chunks: List[str] = None
    ) -> QualityScore:
        """
        使用 LLM 综合评估（更精确但更慢）
        """
        context_text = "\n---\n".join(retrieved_chunks) if retrieved_chunks else context

        prompt = f"""作为一个回答质量评估专家，请综合评估以下回答的质量。

问题：{question}

上下文/检索内容：
{context_text}

回答：
{answer}

请从以下五个方面评估（每个方面0-1分）：
1. 忠实度：回答是否完全基于上下文
2. 相关性：回答是否与问题相关
3. 清晰度：回答是否清晰易懂
4. 完整性：回答是否完整地回答了问题
5. 连贯性：回答逻辑是否连贯

请以JSON格式返回：
{{
    "overall_score": 0-1,
    "clarity_score": 0-1,
    "completeness_score": 0-1,
    "coherence_score": 0-1,
    "explanation": "简短解释",
    "strengths": ["优点1", "优点2"],
    "weaknesses": ["缺点1", "缺点2"],
    "suggestions": ["建议1", "建议2"]
}}
"""

        try:
            # 先运行规则评估获取基础评分
            base_score = await self.evaluate(question, context, answer, retrieved_chunks)

            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": "llama3.1:8b",
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False
                    }
                )
                data = response.json()
                result_text = data.get("message", {}).get("content", "")

                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    return QualityScore(
                        overall_score=result.get("overall_score", base_score.overall_score),
                        faithfulness=base_score.faithfulness,
                        relevance=base_score.relevance,
                        clarity_score=result.get("clarity_score", base_score.clarity_score),
                        completeness_score=result.get("completeness_score", base_score.completeness_score),
                        coherence_score=result.get("coherence_score", base_score.coherence_score),
                        explanation=result.get("explanation", base_score.explanation),
                        strengths=result.get("strengths", base_score.strengths),
                        weaknesses=result.get("weaknesses", base_score.weaknesses),
                        suggestions=result.get("suggestions", base_score.suggestions)
                    )
        except Exception as e:
            print(f"LLM 评估失败: {e}")

        # LLM 失败时回退到规则评估
        return await self.evaluate(question, context, answer, retrieved_chunks)
