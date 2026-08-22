#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
相关性评估器 - 评估检索结果和回答的相关性
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import httpx
import json


@dataclass
class RelevanceScore:
    """相关性评分"""
    retrieval_relevance_score: float
    answer_relevance_score: float
    overall_relevance_score: float
    explanation: str
    relevant_chunks: List[str] = field(default_factory=list)
    irrelevant_chunks: List[str] = field(default_factory=list)


class RelevanceEvaluator:
    """相关性评估器"""

    def __init__(self, ollama_url: str = "http://192.168.3.105:11434"):
        self.ollama_url = ollama_url

    async def evaluate_retrieval(
        self,
        question: str,
        retrieved_chunks: List[str]
    ) -> RelevanceScore:
        """
        评估检索结果的相关性

        Args:
            question: 用户问题
            retrieved_chunks: 检索到的文档片段

        Returns:
            RelevanceScore: 评分结果
        """
        if not retrieved_chunks:
            return RelevanceScore(
                retrieval_relevance_score=0.0,
                answer_relevance_score=0.0,
                overall_relevance_score=0.0,
                explanation="没有检索到任何文档片段。"
            )

        relevant_chunks = []
        irrelevant_chunks = []

        for chunk in retrieved_chunks:
            is_relevant = await self._is_chunk_relevant(question, chunk)
            if is_relevant:
                relevant_chunks.append(chunk)
            else:
                irrelevant_chunks.append(chunk)

        retrieval_relevance = len(relevant_chunks) / len(retrieved_chunks)
        explanation = self._generate_retrieval_explanation(
            retrieval_relevance,
            len(relevant_chunks),
            len(irrelevant_chunks)
        )

        return RelevanceScore(
            retrieval_relevance_score=retrieval_relevance,
            answer_relevance_score=0.0,  # 还没评估回答
            overall_relevance_score=retrieval_relevance,
            explanation=explanation,
            relevant_chunks=relevant_chunks,
            irrelevant_chunks=irrelevant_chunks
        )

    async def evaluate_answer(
        self,
        question: str,
        answer: str
    ) -> RelevanceScore:
        """
        评估回答的相关性

        Args:
            question: 用户问题
            answer: 生成的回答

        Returns:
            RelevanceScore: 评分结果
        """
        relevance_score = await self._calculate_answer_relevance(question, answer)

        explanation = self._generate_answer_explanation(relevance_score)

        return RelevanceScore(
            retrieval_relevance_score=0.0,  # 没评估检索
            answer_relevance_score=relevance_score,
            overall_relevance_score=relevance_score,
            explanation=explanation
        )

    async def evaluate_combined(
        self,
        question: str,
        retrieved_chunks: List[str],
        answer: str
    ) -> RelevanceScore:
        """
        评估检索和回答的综合相关性
        """
        retrieval_score = await self.evaluate_retrieval(question, retrieved_chunks)
        answer_score = await self.evaluate_answer(question, answer)

        overall_score = (
            retrieval_score.retrieval_relevance_score * 0.4 +
            answer_score.answer_relevance_score * 0.6
        )

        explanation = f"检索相关性: {retrieval_score.retrieval_relevance_score:.2f}, " \
                     f"回答相关性: {answer_score.answer_relevance_score:.2f}"

        return RelevanceScore(
            retrieval_relevance_score=retrieval_score.retrieval_relevance_score,
            answer_relevance_score=answer_score.answer_relevance_score,
            overall_relevance_score=overall_score,
            explanation=explanation,
            relevant_chunks=retrieval_score.relevant_chunks,
            irrelevant_chunks=retrieval_score.irrelevant_chunks
        )

    async def _is_chunk_relevant(self, question: str, chunk: str) -> bool:
        """检查文档片段是否与问题相关"""
        if not question or not chunk:
            return False

        # 提取关键词
        question_keywords = self._extract_keywords(question.lower())
        chunk_lower = chunk.lower()

        # 关键词匹配
        match_count = 0
        for keyword in question_keywords:
            if keyword in chunk_lower:
                match_count += 1

        # 至少有 20% 的关键词匹配
        return match_count >= max(1, len(question_keywords) * 0.2)

    async def _calculate_answer_relevance(self, question: str, answer: str) -> float:
        """计算回答的相关性"""
        if not question or not answer:
            return 0.0

        # 提取关键词
        question_keywords = set(self._extract_keywords(question.lower()))
        answer_words = set(self._extract_keywords(answer.lower()))

        if not question_keywords:
            return 0.0

        # 词汇重叠
        intersection = question_keywords & answer_words
        overlap_score = len(intersection) / len(question_keywords)

        # 长度因素：太短的回答可能不够
        length_score = min(1.0, len(answer) / 100)

        return overlap_score * 0.6 + length_score * 0.4

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        words = re.findall(r'\b[\w\u4e00-\u9fa5]+\b', text)
        keywords = [word for word in words if len(word) > 1]
        return keywords[:20]

    def _generate_retrieval_explanation(
        self,
        score: float,
        relevant_count: int,
        irrelevant_count: int
    ) -> str:
        """生成检索解释"""
        if score >= 0.8:
            return "检索结果与问题高度相关。"
        elif score >= 0.5:
            return f"检索结果部分相关，{relevant_count} 个相关，{irrelevant_count} 个不相关。"
        elif score >= 0.2:
            return "检索结果相关性较低。"
        else:
            return "检索结果与问题几乎不相关。"

    def _generate_answer_explanation(self, score: float) -> str:
        """生成回答解释"""
        if score >= 0.8:
            return "回答与问题高度相关。"
        elif score >= 0.5:
            return "回答与问题部分相关。"
        elif score >= 0.2:
            return "回答与问题相关性较低。"
        else:
            return "回答与问题几乎不相关。"

    async def evaluate_with_llm(
        self,
        question: str,
        retrieved_chunks: List[str],
        answer: str
    ) -> RelevanceScore:
        """
        使用 LLM 评估相关性（更精确但更慢）
        """
        context_text = "\n---\n".join(retrieved_chunks)

        prompt = f"""作为一个相关性评估专家，请评估以下检索和回答的相关性。

问题：{question}

检索到的内容：
{context_text}

生成的回答：
{answer}

请从以下三个方面评估：
1. 检索相关性：检索到的内容是否与问题相关（0-1）
2. 回答相关性：回答是否与问题相关（0-1）
3. 综合相关性：两者的综合得分（0-1）

请以JSON格式返回：
{{
    "retrieval_relevance_score": 0-1,
    "answer_relevance_score": 0-1,
    "overall_relevance_score": 0-1,
    "explanation": "简短解释",
    "relevant_chunks": ["相关片段1", "相关片段2"],
    "irrelevant_chunks": ["不相关片段1"]
}}
"""

        try:
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
                    return RelevanceScore(
                        retrieval_relevance_score=result.get("retrieval_relevance_score", 0.5),
                        answer_relevance_score=result.get("answer_relevance_score", 0.5),
                        overall_relevance_score=result.get("overall_relevance_score", 0.5),
                        explanation=result.get("explanation", ""),
                        relevant_chunks=result.get("relevant_chunks", []),
                        irrelevant_chunks=result.get("irrelevant_chunks", [])
                    )
        except Exception as e:
            print(f"LLM 评估失败: {e}")

        # LLM 失败时回退到规则评估
        return await self.evaluate_combined(question, retrieved_chunks, answer)
